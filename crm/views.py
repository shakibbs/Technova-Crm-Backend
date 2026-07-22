"""
CRM ViewSets for internal staff (Project, Milestone, Task).

All are guarded by IsAgencyStaff -> only employees/admins can reach them.
List queries use select_related/prefetch_related to avoid N+1 lookups
(per the SRS performance requirements).
"""
from django.db.models import Count, Q

from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from accounts.models import ClientProfile, EmployeeProfile, User
from accounts.permissions import IsAdmin, IsAgencyStaff
from .models import Lead, Milestone, Project, Proposal, ProposalMessage, Task, ClientProjectRequest
from .notify import send_client_credentials
from .serializers import (
    ClientDetailSerializer, ClientProfileSerializer,
    EmployeeCreateSerializer, EmployeeListSerializer,
    LeadSerializer, MilestoneSerializer, ProjectSerializer,
    ProposalMessageSerializer, ProposalSerializer, PublicLeadSerializer,
    TaskSerializer, TaskUpdateSerializer, ClientProjectRequestSerializer
)
from .services import _generate_temp_password
from .services import (
    accept_counter_offer, accept_proposal, convert_lead, reject_proposal,
)


class ProjectViewSet(viewsets.ModelViewSet):
    """CRUD for projects (/api/v1/crm/projects/)."""
    queryset = Project.objects.select_related('client').prefetch_related('tasks')
    serializer_class = ProjectSerializer
    filterset_fields = ['status', 'client']   # ?status=in_progress&client=<uuid>
    search_fields = ['title', 'description']  # ?search=...
    ordering_fields = ['created_at', 'start_date', 'target_end_date']

    def get_permissions(self):
        """Admin-only: create, update, delete. Employees: view only (no status change)."""
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdmin()]
        return [IsAgencyStaff()]

    def get_queryset(self):
        # Annotate task counts so the serializer can render dashboard progress.
        return super().get_queryset().annotate(
            task_count=Count('tasks', distinct=True),
            completed_task_count=Count('tasks', filter=Q(tasks__status='done'), distinct=True),
            unread_messages_count=Count('messages', filter=Q(messages__is_read_by_staff=False), distinct=True),
        )

    def retrieve(self, request, *args, **kwargs):
        """When a staff member opens a project, clear its unread messages."""
        instance = self.get_object()
        from .models import ProjectMessage
        ProjectMessage.objects.filter(project=instance, is_read_by_staff=False).update(is_read_by_staff=True)
        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=['get', 'post'], url_path='messages')
    def messages(self, request, pk=None):
        """GET/POST /crm/projects/<uuid>/messages/ -> thread for the project."""
        from .portal_serializers import PortalProjectMessageSerializer
        project = self.get_object()
        
        if request.method == 'GET':
            from .models import ProjectMessage
            # Ensure staff sees all messages and it marks unread as read (just in case they ping this directly)
            ProjectMessage.objects.filter(project=project, is_read_by_staff=False).update(is_read_by_staff=True)
            serializer = PortalProjectMessageSerializer(project.messages.all(), many=True)
            return Response(serializer.data)
            
        serializer = PortalProjectMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Admins posting a message
        msg = serializer.save(project=project, author=request.user, is_read_by_staff=True)
        return Response(PortalProjectMessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class MilestoneViewSet(viewsets.ModelViewSet):
    """CRUD for milestones (/api/v1/crm/milestones/)."""
    queryset = Milestone.objects.select_related('project')
    serializer_class = MilestoneSerializer
    filterset_fields = ['project', 'is_completed']

    def get_permissions(self):
        """Admin-only: create + delete. Employees: view only."""
        if self.action in ('create', 'destroy'):
            return [IsAdmin()]
        return [IsAgencyStaff()]


class TaskViewSet(viewsets.ModelViewSet):
    """CRUD for tasks (/api/v1/crm/tasks/).

    Employees see only tasks assigned to them and can update status.
    Admins have full CRUD on all tasks.
    """
    queryset = Task.objects.select_related('project', 'assignee')
    serializer_class = TaskSerializer
    filterset_fields = ['project', 'assignee', 'status', 'priority']
    search_fields = ['title', 'description']
    ordering_fields = ['due_date', 'priority', 'status']

    def get_permissions(self):
        """Admin-only: create + delete. Employees: view + update own tasks."""
        if self.action in ('create', 'destroy'):
            return [IsAdmin()]
        return [IsAgencyStaff()]

    def get_queryset(self):
        """Employees see only their own assigned tasks; admins see all."""
        qs = super().get_queryset()
        if self.request.user.role != 'admin':
            qs = qs.filter(assignee=self.request.user)
        return qs

    def perform_create(self, serializer):
        """Create the task, then email the assigned employee."""
        super().perform_create(serializer)
        # Notify the newly assigned employee (non-blocking)
        try:
            from .notify import notify_task_assignment
            notify_task_assignment(serializer.instance)
        except Exception:
            pass

    def perform_update(self, serializer):
        """Only the assigned employee may change a task's status.

        Admins can still edit other fields (title, assignee, priority, due_date)
        — they just cannot set the status. This keeps task delivery ownership
        with the person doing the work. If the assignee changes, the new
        employee is notified by email.
        """
        if 'status' in serializer.validated_data:
            if serializer.instance.assignee_id != self.request.user.id:
                raise PermissionDenied(
                    'Only the employee assigned to this task can change its status.')
        old_assignee_id = serializer.instance.assignee_id
        super().perform_update(serializer)
        # Notify the employee if the task was reassigned to someone new
        new_assignee_id = serializer.instance.assignee_id
        if new_assignee_id and new_assignee_id != old_assignee_id:
            try:
                from .notify import notify_task_assignment
                notify_task_assignment(serializer.instance)
            except Exception:
                pass

    @action(detail=True, methods=['get', 'post'], url_path='updates')
    def updates(self, request, pk=None):
        """GET/POST /crm/tasks/<uuid>/updates/ -> list or add a progress/issue/reply.

        Employees can only post on tasks assigned to them (enforced by
        get_queryset scoping on the parent object lookup). Admins can reply to
        any task.
        """
        task = self.get_object()  # respects get_queryset (employees -> own tasks)
        if request.method == 'GET':
            serializer = TaskUpdateSerializer(task.updates.all(), many=True)
            return Response(serializer.data)
        # POST: create a new update entry
        serializer = TaskUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update = serializer.save(task=task, author=request.user)
        return Response(TaskUpdateSerializer(update).data, status=status.HTTP_201_CREATED)


class LeadViewSet(viewsets.ModelViewSet):
    """
    Staff lead management (/api/v1/crm/leads/).

    Supports the standard CRUD plus a custom `convert` action that runs the
    Lead -> Client conversion engine.
    """
    queryset = Lead.objects.select_related('converted_client')
    serializer_class = LeadSerializer
    filterset_fields = ['status', 'source']     # ?status=new
    search_fields = ['name', 'email', 'company']
    ordering_fields = ['created_at', 'status']

    def get_permissions(self):
        """Admin-only: full lead management (incl. single-lead detail).
        Employees may only browse the lead list — they cannot open or manage a single lead."""
        if self.action in ('create', 'retrieve', 'update', 'partial_update', 'destroy', 'convert'):
            return [IsAdmin()]
        return [IsAgencyStaff()]

    @action(detail=True, methods=['post'], url_path='convert')
    def convert(self, request, pk=None):
        """POST /api/v1/crm/leads/<uuid>/convert/ -> create a client account."""
        lead = self.get_object()
        try:
            client_profile = convert_lead(lead)  # transactional conversion
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {'detail': 'Lead converted successfully.',
             'client_id': str(client_profile.id),
             'client_email': lead.email},
            status=status.HTTP_201_CREATED,
        )

class ClientProjectRequestViewSet(viewsets.ModelViewSet):
    """
    Staff management of existing client project requests (/api/v1/crm/project-requests/).
    """
    queryset = ClientProjectRequest.objects.select_related('client__user')
    serializer_class = ClientProjectRequestSerializer
    filterset_fields = ['status', 'client']
    search_fields = ['title', 'description', 'client__company_name', 'client__user__email']
    ordering_fields = ['created_at', 'status']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdmin()]
        return [IsAgencyStaff()]


class ProposalViewSet(viewsets.ModelViewSet):
    """
    Staff proposal management (/api/v1/crm/proposals/).

    Negotiation flow (bidirectional counter-offer):
      1. Staff creates proposal (budget, timeline, scope) -> send
      2. Client can: ACCEPT (project created) | REJECT (with reason) | NEGOTIATE (counter-offer)
      3. Staff can do the same on a client counter-offer
      4. Loop until one side accepts the other's terms -> Project auto-created

    Custom actions:
      /send/             -> mark Sent (client sees it in portal)
      /accept/           -> accept the proposal's current figures as-is
      /negotiate/        -> send a counter-offer with new budget/timeline/scope
      /messages/<id>/accept_counter/ -> accept a specific counter-offer
      /reject/           -> reject with a reason message
    """
    queryset = Proposal.objects.select_related('client', 'lead', 'linked_project').prefetch_related('messages')
    serializer_class = ProposalSerializer
    filterset_fields = ['status', 'client']
    search_fields = ['title', 'scope']
    ordering_fields = ['created_at', 'proposed_budget']

    def get_permissions(self):
        """Admin-only: create, delete, send, accept, negotiate, reject.
        Employees: view only."""
        if self.action in ('create', 'destroy', 'send', 'accept',
                           'negotiate', 'accept_counter', 'reject'):
            return [IsAdmin()]
        return [IsAgencyStaff()]

    def _sync_lead_status(self, proposal, lead_status):
        """Mirror the proposal lifecycle onto the originating lead's pipeline status."""
        if proposal.lead_id and proposal.lead.status != Lead.Status.LOST:
            proposal.lead.status = lead_status
            proposal.lead.save(update_fields=['status'])

    @action(detail=True, methods=['post'], url_path='send')
    def send(self, request, pk=None):
        """POST /proposals/<uuid>/send/ -> mark Sent (client sees it in portal)."""
        proposal = self.get_object()
        proposal.status = Proposal.Status.SENT
        proposal.save(update_fields=['status'])
        self._sync_lead_status(proposal, Lead.Status.CONTACTED)
        # Notify the client that a proposal is ready for review
        try:
            from .notify import notify_proposal_sent
            notify_proposal_sent(proposal)
        except Exception:
            pass  # email failure should not block the send action
        return Response({'detail': 'Proposal sent to client portal.'})

    @action(detail=True, methods=['post'], url_path='accept')
    def accept(self, request, pk=None):
        """POST /proposals/<uuid>/accept/ -> accept current figures, create Project."""
        proposal = self.get_object()
        project = accept_proposal(proposal)  # transactional auto-creation
        self._sync_lead_status(proposal, Lead.Status.QUALIFIED)
        return Response(
            {'detail': 'Proposal accepted; project created.',
             'project_id': str(project.id), 'project_title': project.title},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='negotiate')
    def negotiate(self, request, pk=None):
        """
        POST /proposals/<uuid>/negotiate/ -> send a counter-offer.

        Body: {body, proposed_budget, proposed_start_date, proposed_end_date, proposed_scope?}
        Sets proposal status to NEGOTIATING and records the counter-offer message.
        """
        proposal = self.get_object()
        serializer = ProposalMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Mark any previous pending counter-offers as superseded
        proposal.messages.filter(
            message_type=ProposalMessage.MessageType.COUNTER_OFFER,
            offer_status=ProposalMessage.OfferStatus.PENDING,
        ).update(offer_status=ProposalMessage.OfferStatus.SUPERSEDED)

        message = serializer.save(
            proposal=proposal,
            author=request.user,
            message_type=ProposalMessage.MessageType.COUNTER_OFFER,
        )

        # Move proposal to NEGOTIATING state
        proposal.status = Proposal.Status.NEGOTIATING
        proposal.save(update_fields=['status'])

        return Response(
            {'detail': 'Counter-offer sent.', 'message': ProposalMessageSerializer(message).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='messages/(?P<message_id>[^/.]+)/accept_counter')
    def accept_counter(self, request, pk=None, message_id=None):
        """
        POST /proposals/<uuid>/messages/<msg_id>/accept_counter/
        -> accept a specific counter-offer, merge figures, create Project.
        """
        proposal = self.get_object()
        message = proposal.messages.get(id=message_id)  # 404 if not found
        project = accept_counter_offer(message)
        self._sync_lead_status(proposal, Lead.Status.QUALIFIED)
        return Response(
            {'detail': 'Counter-offer accepted; project created.',
             'project_id': str(project.id),
             'final_budget': str(proposal.proposed_budget)},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """
        POST /proposals/<uuid>/reject/
        -> reject with a reason. Body: {reason: "..."}
        """
        proposal = self.get_object()
        reason = request.data.get('reason', '')
        if not reason:
            return Response({'detail': 'A rejection reason is required.'},
                            status=status.HTTP_400_BAD_REQUEST)
        reject_proposal(proposal, request.user, reason)
        self._sync_lead_status(proposal, Lead.Status.LOST)
        return Response({'detail': 'Proposal rejected.', 'reason': reason})

    @action(detail=True, methods=['get', 'post'], url_path='messages')
    def messages(self, request, pk=None):
        """GET/POST /proposals/<uuid>/messages/ -> list or add a plain message."""
        proposal = self.get_object()
        if request.method == 'GET':
            msgs = proposal.messages.all()
            return Response(ProposalMessageSerializer(msgs, many=True).data)
        # POST: create a plain message
        serializer = ProposalMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(proposal=proposal, author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ClientListView(generics.ListAPIView):
    """List every real client account (staff only).

    A ClientProfile only exists once someone is an actual client — either
    created by converting a Lead or created directly. Leads that have NOT been
    converted never have a ClientProfile, so they never appear here. This is
    the authoritative client list.
    """
    serializer_class = ClientProfileSerializer
    permission_classes = [IsAgencyStaff]

    def get_queryset(self):
        return ClientProfile.objects.select_related('user')


class ClientDetailView(generics.RetrieveAPIView):
    """Retrieve a single client's full profile + engagement stats (staff only)."""
    serializer_class = ClientDetailSerializer
    permission_classes = [IsAgencyStaff]
    queryset = ClientProfile.objects.select_related('user')


# ── Employee Management (admin-controlled) ──────────────────────────────────

class EmployeeListView(generics.ListAPIView):
    """List all employees for task assignment dropdowns + team page."""
    serializer_class = EmployeeListSerializer
    permission_classes = [IsAgencyStaff]
    queryset = EmployeeProfile.objects.select_related('user').all()


class EmployeeCreateView(generics.CreateAPIView):
    """
    Admin-only: create a new employee account.

    The password is auto-generated server-side and emailed to the employee.
    The admin never sees or handles the password. Uses the same email
    infrastructure as the lead-to-client conversion flow.
    """
    serializer_class = EmployeeCreateSerializer
    permission_classes = [IsAdmin]

    def perform_create(self, serializer):
        """Create User(role=employee) + EmployeeProfile, then email credentials."""
        data = serializer.validated_data
        temp_password = _generate_temp_password()

        user = User.objects.create_user(
            email=data['email'],
            password=temp_password,
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            role=User.Role.EMPLOYEE,
        )
        profile = EmployeeProfile.objects.create(
            user=user,
            department=data.get('department', ''),
        )

        # Email the temp password (non-blocking) — employee account type
        try:
            emp_name = f"{user.first_name} {user.last_name}".strip()
            send_client_credentials(user.email, temp_password,
                                    account_type='employee', recipient_name=emp_name)
        except Exception:
            pass  # email failure should not block account creation

        # Return the created profile via the list serializer
        return EmployeeListSerializer(profile).data

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)


class EmployeeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin-only: retrieve, edit, or deactivate an employee.

    PATCH updates first_name, last_name, department, and is_active.
    DELETE deactivates (soft delete) by setting is_active=False — never
    hard-deletes to preserve task assignment history.
    """
    serializer_class = EmployeeListSerializer
    permission_classes = [IsAdmin]
    queryset = EmployeeProfile.objects.select_related('user').all()

    def update(self, request, *args, **kwargs):
        """Handle PATCH: update User fields + EmployeeProfile fields."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        data = request.data

        # Update User fields
        user = instance.user
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'is_active' in data:
            user.is_active = data['is_active']
        user.save()

        # Update EmployeeProfile fields
        if 'department' in data:
            instance.department = data['department']
        instance.save()

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        """Soft delete: deactivate the user account, never hard-delete."""
        instance.user.is_active = False
        instance.user.save()


class PublicLeadCreateView(generics.CreateAPIView):
    """
    Public "Contact Us" intake (/api/v1/public/leads/).

    Anonymous, throttled (AnonRateThrottle -> 30/hour) to mitigate spam/bots.
    A real bot-mitigation token check (Turnstile/reCAPTCHA) plugs in here in
    Phase 5; for now captcha_verified is set true in the serializer.
    """
    queryset = Lead.objects.all()
    serializer_class = PublicLeadSerializer
    permission_classes = [AllowAny]            # anyone can submit a contact form
    throttle_classes = [AnonRateThrottle]      # anti-spam rate limit

    def perform_create(self, serializer):
        """Save the lead, then fire off a staff notification email (non-blocking)."""
        lead = serializer.save()
        try:
            from .tasks import send_lead_notification
            send_lead_notification.delay(str(lead.id))
        except Exception:
            # Email notification failure must never break lead creation
            pass
