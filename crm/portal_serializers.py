"""
Client-portal serializers (read-mostly, stripped of staff-only fields).

These serializers are what a logged-in CLIENT sees in their portal. They
deliberately omit internal fields (internal notes, assignee emails, etc.)
and are always scoped to the requesting client's own records.
"""
from rest_framework import serializers

from .models import Milestone, Project, Proposal, ProposalMessage, Task


class PortalMilestoneSerializer(serializers.ModelSerializer):
    """Client-facing milestone view (no internal cost/effort fields)."""

    class Meta:
        model = Milestone
        fields = ['id', 'title', 'description', 'due_date', 'is_completed', 'created_at']
        read_only_fields = fields  # clients cannot edit milestones


class PortalTaskSerializer(serializers.ModelSerializer):
    """Client-facing task view — status + title only, no assignee details."""

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'status', 'priority', 'due_date']
        read_only_fields = fields  # read-only for clients


class PortalProjectSerializer(serializers.ModelSerializer):
    """
    Client-facing project view with progress stats.

    Includes milestones and task counts so the portal dashboard can render
    a progress bar without extra requests.
    """
    milestones = PortalMilestoneSerializer(many=True, read_only=True)   # nested
    task_count = serializers.IntegerField(read_only=True)               # annotated
    completed_task_count = serializers.IntegerField(read_only=True)      # annotated

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'description', 'status',
            'start_date', 'target_end_date',
            'milestones', 'task_count', 'completed_task_count', 'created_at',
        ]
        read_only_fields = fields  # fully read-only for clients


class PortalProposalMessageSerializer(serializers.ModelSerializer):
    """Client-facing negotiation message (shows author email for context)."""

    author_email = serializers.CharField(source='author.email', read_only=True)

    class Meta:
        model = ProposalMessage
        fields = [
            'id', 'author', 'author_email', 'body', 'message_type',
            'proposed_budget', 'proposed_start_date', 'proposed_end_date',
            'proposed_scope', 'offer_status', 'created_at',
        ]
        read_only_fields = ['id', 'author', 'author_email', 'offer_status', 'created_at']
        extra_kwargs = {'proposal': {'required': False}}  # set from URL


class PortalProposalSerializer(serializers.ModelSerializer):
    """
    Client-facing proposal view with the negotiation thread nested.

    Clients see the full figures (budget, timeline, scope) and can respond
    with accept / negotiate / reject via the portal view actions.
    """
    messages = PortalProposalMessageSerializer(many=True, read_only=True)
    linked_project_id = serializers.UUIDField(read_only=True)  # project UUID if accepted

    class Meta:
        model = Proposal
        fields = [
            'id', 'title', 'scope', 'proposed_budget',
            'proposed_start_date', 'proposed_end_date', 'technologies',
            'status', 'linked_project_id', 'messages', 'created_at',
        ]
        read_only_fields = fields  # clients cannot edit proposal figures directly
