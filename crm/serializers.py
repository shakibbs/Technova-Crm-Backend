"""
DRF serializers for the CRM app (Project, Milestone, Task).

These convert model instances <-> JSON and validate incoming payloads.
"""
from rest_framework import serializers

from accounts.models import ClientProfile, EmployeeProfile
from .models import (
    Lead, Milestone, Project, Proposal, ProposalMessage, Task, TaskUpdate, 
    ClientProjectRequest
)


class ClientProfileSerializer(serializers.ModelSerializer):
    """Lightweight client serializer for dropdown selectors (project creation)."""

    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = ClientProfile
        fields = ['id', 'email', 'company_name', 'industry']


class ClientDetailSerializer(serializers.ModelSerializer):
    """Rich client profile for the client detail page — full info + engagement stats."""

    email = serializers.CharField(source='user.email', read_only=True)
    date_joined = serializers.DateTimeField(source='user.date_joined', read_only=True)
    first_contact = serializers.SerializerMethodField(read_only=True)
    projects = serializers.SerializerMethodField(read_only=True)
    project_count = serializers.SerializerMethodField(read_only=True)
    completed_project_count = serializers.SerializerMethodField(read_only=True)
    active_project_count = serializers.SerializerMethodField(read_only=True)
    total_tasks = serializers.SerializerMethodField(read_only=True)
    completed_tasks = serializers.SerializerMethodField(read_only=True)
    proposal_count = serializers.SerializerMethodField(read_only=True)
    total_budget = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ClientProfile
        fields = [
            'id', 'email', 'company_name', 'industry', 'billing_address',
            'date_joined', 'first_contact',
            'projects', 'project_count', 'completed_project_count', 'active_project_count',
            'total_tasks', 'completed_tasks', 'proposal_count', 'total_budget',
        ]

    def get_first_contact(self, obj):
        lead = obj.leads.order_by('created_at').first()
        return lead.created_at if lead else (obj.user.date_joined if obj.user_id else None)

    def get_projects(self, obj):
        from .models import Task
        projects = []
        for p in obj.projects.all():
            tasks = p.tasks.all()
            total = tasks.count()
            done = tasks.filter(status=Task.Status.DONE).count()
            projects.append({
                'id': str(p.id),
                'title': p.title,
                'status': p.status,
                'created_at': p.created_at,
                'start_date': p.start_date,
                'target_end_date': p.target_end_date,
                'task_count': total,
                'completed_task_count': done,
            })
        return projects

    def _projects(self, obj):
        return obj.projects.all()

    def get_project_count(self, obj):
        return self._projects(obj).count()

    def get_completed_project_count(self, obj):
        return self._projects(obj).filter(status='completed').count()

    def get_active_project_count(self, obj):
        return self._projects(obj).exclude(status='completed').count()

    def get_total_tasks(self, obj):
        from .models import Task
        return Task.objects.filter(project__client=obj).count()

    def get_completed_tasks(self, obj):
        from .models import Task
        return Task.objects.filter(project__client=obj, status=Task.Status.DONE).count()

    def get_proposal_count(self, obj):
        return obj.proposals.count() if hasattr(obj, 'proposals') else 0

    def get_total_budget(self, obj):
        from django.db.models import Sum
        # Total contract value from accepted (won) proposals.
        total = obj.proposals.filter(status='accepted').aggregate(s=Sum('proposed_budget'))['s']
        return str(total or 0)
        read_only_fields = fields


class EmployeeListSerializer(serializers.ModelSerializer):
    """Employee serializer for team page + task assignment dropdowns."""

    user_id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    role = serializers.CharField(source='user.role', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeProfile
        fields = [
            'id', 'user_id', 'email', 'first_name', 'last_name',
            'full_name', 'department', 'role', 'is_active', 'hire_date',
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        """Return 'First Last' or fall back to email if no name set."""
        name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return name or obj.user.email


class EmployeeCreateSerializer(serializers.Serializer):
    """Write serializer for admin creating a new employee account.

    The password is auto-generated server-side and emailed to the employee.
    The admin never sees or handles the password.
    """

    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    department = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_email(self, value):
        """Ensure no duplicate account."""
        from accounts.models import User
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value


class MilestoneSerializer(serializers.ModelSerializer):
    """Read/write serializer for project milestones."""

    class Meta:
        model = Milestone
        fields = ['id', 'project', 'title', 'due_date', 'is_completed', 'created_at']
        read_only_fields = ['id', 'created_at']  # server-managed fields


class TaskUpdateSerializer(serializers.ModelSerializer):
    """Serializer for task progress reports, issues, and admin replies.

    `author_name` + `author_role` are read-only display fields so the frontend
    can show who wrote each entry without extra lookups.
    """
    author_name = serializers.SerializerMethodField(read_only=True)
    author_role = serializers.CharField(source='author.role', read_only=True)

    class Meta:
        model = TaskUpdate
        fields = [
            'id', 'task', 'author', 'author_name', 'author_role',
            'update_type', 'body', 'created_at',
        ]
        read_only_fields = ['id', 'task', 'author', 'author_name', 'author_role', 'created_at']

    def get_author_name(self, obj):
        """Return 'First Last' or email for the author, 'System' if the user was deleted."""
        if not obj.author:
            return 'System'
        name = f'{obj.author.first_name} {obj.author.last_name}'.strip()
        return name or obj.author.email


class TaskSerializer(serializers.ModelSerializer):
    """Read/write serializer for tasks.

    `assignee_email` lets staff assign by email instead of fiddling with user IDs.
    `assignee_name` is a read-only display field so the frontend can show who's assigned.
    """
    assignee_email = serializers.EmailField(
        write_only=True, required=False, allow_blank=True,
        help_text='Email of the employee to assign this task to.')
    assignee_name = serializers.SerializerMethodField(read_only=True)
    updates = TaskUpdateSerializer(many=True, read_only=True)  # nested collaboration thread

    class Meta:
        model = Task
        fields = [
            'id', 'project', 'assignee', 'assignee_email', 'assignee_name',
            'title', 'description', 'priority', 'status', 'due_date', 'created_at',
            'updates',
        ]
        read_only_fields = ['id', 'assignee', 'assignee_name', 'updates', 'created_at']

    def get_assignee_name(self, obj):
        """Return 'First Last' or email for the assignee, empty string if unassigned."""
        if not obj.assignee:
            return ''
        name = f'{obj.assignee.first_name} {obj.assignee.last_name}'.strip()
        return name or obj.assignee.email

    def create(self, validated_data):
        email = validated_data.pop('assignee_email', None)  # pull out before save
        task = Task.objects.create(**validated_data)
        if email:
            from accounts.models import User
            task.assignee = User.objects.filter(email=email).first()  # None if not found
            task.save()
        return task

    def update(self, instance, validated_data):
        """Handle re-assignment via assignee_email on PATCH."""
        email = validated_data.pop('assignee_email', None)
        instance = super().update(instance, validated_data)
        if email is not None:
            from accounts.models import User
            instance.assignee = User.objects.filter(email=email).first() if email else None
            instance.save()
        return instance


class PublicLeadSerializer(serializers.ModelSerializer):
    """
    Input serializer for the public "Contact Us" form (/api/v1/public/leads/).

    Anonymous: only the fields a visitor fills in. status/source are forced
    server-side so the public can't spoof them.
    """

    class Meta:
        model = Lead
        fields = ['name', 'email', 'phone', 'company', 'message', 'desired_deadline']
        extra_kwargs = {  # all listed fields are required from the visitor
            'name': {'required': True},
            'email': {'required': True},
            'message': {'required': True},
        }

    def create(self, validated_data):
        # Force safe defaults the public must not control
        validated_data['status'] = Lead.Status.NEW
        validated_data['source'] = 'website'
        validated_data['captcha_verified'] = True  # set by the view after bot check
        return super().create(validated_data)


class LeadSerializer(serializers.ModelSerializer):
    """Staff-facing serializer for managing leads in the CRM dashboard."""

    converted_client = serializers.StringRelatedField(read_only=True)  # shows company/email
    converted_client_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = Lead
        fields = [
            'id', 'name', 'email', 'phone', 'company', 'message', 'desired_deadline',
            'source', 'status', 'captcha_verified', 'converted_client', 'converted_client_id',
            'created_at',
        ]
        read_only_fields = ['id', 'converted_client', 'converted_client_id', 'created_at', 'captcha_verified']


class ClientProjectRequestSerializer(serializers.ModelSerializer):
    """Staff-facing serializer for reviewing client project requests."""
    
    client_name = serializers.CharField(source='client.company_name', read_only=True)
    client_email = serializers.CharField(source='client.user.email', read_only=True)

    class Meta:
        model = ClientProjectRequest
        fields = [
            'id', 'client', 'client_name', 'client_email', 'title', 
            'description', 'desired_deadline', 'proposed_budget', 
            'status', 'created_at'
        ]
        read_only_fields = ['id', 'client', 'client_name', 'client_email', 'created_at']

class ProjectSerializer(serializers.ModelSerializer):
    """Project serializer with aggregated counts for dashboard cards."""

    task_count = serializers.IntegerField(read_only=True)        # annotated in the viewset
    completed_task_count = serializers.IntegerField(read_only=True)
    unread_messages_count = serializers.IntegerField(read_only=True, required=False)
    client_name = serializers.SerializerMethodField(read_only=True)
    client_email = serializers.SerializerMethodField(read_only=True)
    client_industry = serializers.SerializerMethodField(read_only=True)
    client_billing_address = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'description', 'status', 'client',
            'client_name', 'client_email', 'client_industry', 'client_billing_address',
            'start_date', 'target_end_date', 'created_at',
            'task_count', 'completed_task_count', 'unread_messages_count',
        ]
        read_only_fields = ['id', 'created_at']

    def _client(self, obj):
        return obj.client

    def get_client_name(self, obj):
        client = self._client(obj)
        if not client:
            return None
        return client.company_name or (client.user.email if client.user_id else None)

    def get_client_email(self, obj):
        client = self._client(obj)
        return client.user.email if client and client.user_id else None

    def get_client_industry(self, obj):
        client = self._client(obj)
        return client.industry if client else None

    def get_client_billing_address(self, obj):
        client = self._client(obj)
        return client.billing_address if client else None


class ProposalMessageSerializer(serializers.ModelSerializer):
    """
    One message in a proposal's negotiation thread.

    For a COUNTER_OFFER the sender must also provide proposed_budget,
    proposed_start_date, proposed_end_date (and optionally proposed_scope).
    For a plain MESSAGE only body is needed (e.g. rejection reason).
    """

    author_email = serializers.CharField(source='author.email', read_only=True)

    class Meta:
        model = ProposalMessage
        fields = [
            'id', 'proposal', 'author', 'author_email', 'body',
            'message_type', 'proposed_budget', 'proposed_start_date',
            'proposed_end_date', 'proposed_scope', 'offer_status', 'created_at',
        ]
        read_only_fields = ['id', 'author', 'author_email', 'offer_status', 'created_at']
        extra_kwargs = {
            'proposal': {'required': False},  # set by the view from the URL
        }


class ProposalSerializer(serializers.ModelSerializer):
    """
    Staff-facing serializer for proposals.

    Staff set all the commercial fields (budget, timeline, scope). The client
    can only read these and negotiate via messages -- never edit them.
    """
    messages = ProposalMessageSerializer(many=True, read_only=True)  # nested negotiation thread

    class Meta:
        model = Proposal
        fields = [
            'id', 'client', 'lead', 'title', 'scope', 'proposed_budget',
            'proposed_start_date', 'proposed_end_date', 'technologies',
            'status', 'linked_project', 'messages', 'created_at',
        ]
        read_only_fields = ['id', 'linked_project', 'messages', 'created_at']
        # status is writable by staff (Draft->Sent->Negotiating->Accepted->Rejected)
        extra_kwargs = {
            'proposed_budget': {'required': True},
            'proposed_start_date': {'required': True},
            'proposed_end_date': {'required': True},
        }

    def create(self, validated_data):
        """Auto-link the originating lead so the proposal lifecycle can
        mirror its pipeline status (contacted -> qualified -> lost)."""
        proposal = super().create(validated_data)
        if not proposal.lead_id and proposal.client_id:
            lead = Lead.objects.filter(converted_client_id=proposal.client_id).first()
            if lead:
                proposal.lead = lead
                proposal.save(update_fields=['lead'])
        return proposal
