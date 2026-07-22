"""
Client-portal views (ownership-scoped).

Every queryset is filtered to the authenticated client's own ClientProfile,
so a client can NEVER see or interact with another client's proposals or
projects — even if they guess a UUID.

Security layers:
  1. IsPortalClient permission (role check at the gateway)
  2. get_queryset() scoped to request.user.client_profile (data isolation)
  3. get_object() goes through the scoped queryset (UUID guessing blocked)
"""
from django.db.models import Count, Q

from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsPortalClient
from .models import Project, Proposal, ProposalMessage
from .portal_serializers import (
    PortalProposalMessageSerializer, PortalProposalSerializer,
    PortalProjectSerializer,
)
from .services import accept_counter_offer, accept_proposal, reject_proposal


class _ClientScopedMixin:
    """Shared base: enforces IsPortalClient + provides the client's profile."""

    permission_classes = [IsAuthenticated, IsPortalClient]

    @property
    def client_profile(self):
        """Shortcut to the logged-in client's ClientProfile."""
        return self.request.user.client_profile


# ── Proposals ────────────────────────────────────────────────────

class PortalProposalViewSet(_ClientScopedMixin, viewsets.ReadOnlyModelViewSet):
    """
    Client proposal portal (/api/v1/portal/proposals/).

    Read-only list/retrieve PLUS three negotiation actions:
      /<id>/accept/    -> accept the current figures (project created)
      /<id>/negotiate/ -> send a counter-offer with new figures
      /<id>/reject/    -> reject with a reason message
      /<id>/messages/  -> view or add to the negotiation thread
    """
    serializer_class = PortalProposalSerializer

    def get_queryset(self):
        # SECURITY: only proposals belonging to THIS client, and never DRAFT
        # (staff drafts are invisible until sent).
        qs = Proposal.objects.filter(
            client=self.client_profile
        ).exclude(status=Proposal.Status.DRAFT).prefetch_related('messages')
        return qs

    # ── Accept: client accepts the proposal's current figures ──

    @action(detail=True, methods=['post'], url_path='accept')
    def accept(self, request, pk=None):
        """POST /portal/proposals/<uuid>/accept/ -> accept figures, create Project."""
        proposal = self.get_object()  # scoped queryset -> 404 if not theirs
        project = accept_proposal(proposal)
        return Response(
            {'detail': 'Proposal accepted! Your project has been created.',
             'project_id': str(project.id)},
            status=status.HTTP_201_CREATED,
        )

    # ── Negotiate: client sends a counter-offer ──

    @action(detail=True, methods=['post'], url_path='negotiate')
    def negotiate(self, request, pk=None):
        """
        POST /portal/proposals/<uuid>/negotiate/
        Body: {body, proposed_budget, proposed_start_date, proposed_end_date, proposed_scope?}
        """
        proposal = self.get_object()
        serializer = PortalProposalMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Supersede any older pending counter-offers in this thread
        proposal.messages.filter(
            message_type=ProposalMessage.MessageType.COUNTER_OFFER,
            offer_status=ProposalMessage.OfferStatus.PENDING,
        ).update(offer_status=ProposalMessage.OfferStatus.SUPERSEDED)

        message = serializer.save(
            proposal=proposal,
            author=request.user,
            message_type=ProposalMessage.MessageType.COUNTER_OFFER,
        )
        proposal.status = Proposal.Status.NEGOTIATING
        proposal.save(update_fields=['status'])

        return Response(
            {'detail': 'Your counter-offer has been sent to our team.',
             'message': PortalProposalMessageSerializer(message).data},
            status=status.HTTP_201_CREATED,
        )

    # ── Reject: client declines with a reason ──

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        """POST /portal/proposals/<uuid>/reject/  Body: {reason: "..."}"""
        proposal = self.get_object()
        reason = request.data.get('reason', '')
        if not reason:
            return Response({'detail': 'Please provide a reason for rejection.'},
                            status=status.HTTP_400_BAD_REQUEST)
        reject_proposal(proposal, request.user, reason)
        return Response({'detail': 'Proposal rejected.', 'reason': reason})

    # ── Accept a specific counter-offer (if staff countered) ──

    @action(detail=True, methods=['post'],
            url_path='messages/(?P<message_id>[^/.]+)/accept_counter')
    def accept_counter(self, request, pk=None, message_id=None):
        """POST /portal/proposals/<uuid>/messages/<msg_id>/accept_counter/"""
        proposal = self.get_object()
        message = proposal.messages.get(id=message_id)  # scoped -> 404 if not theirs
        project = accept_counter_offer(message)
        return Response(
            {'detail': 'Counter-offer accepted! Project created.',
             'project_id': str(project.id)},
            status=status.HTTP_201_CREATED,
        )

    # ── Messages: view or add to the negotiation thread ──

    @action(detail=True, methods=['get', 'post'], url_path='messages')
    def messages(self, request, pk=None):
        """GET/POST /portal/proposals/<uuid>/messages/"""
        proposal = self.get_object()
        if request.method == 'GET':
            msgs = proposal.messages.all()
            return Response(PortalProposalMessageSerializer(msgs, many=True).data)
        serializer = PortalProposalMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(proposal=proposal, author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ── Projects ─────────────────────────────────────────────────────

class PortalProjectViewSet(_ClientScopedMixin, viewsets.ReadOnlyModelViewSet):
    """
    Client project portal (/api/v1/portal/projects/).

    Read-only list + detail. Clients see progress (milestones, task counts)
    but cannot create or modify projects — that's staff-only.
    """
    serializer_class = PortalProjectSerializer

    def get_queryset(self):
        # SECURITY: only projects for THIS client
        return Project.objects.filter(
            client=self.client_profile
        ).prefetch_related('milestones').annotate(
            task_count=Count('tasks'),
            completed_task_count=Count('tasks', filter=Q(tasks__status='done')),
        )
