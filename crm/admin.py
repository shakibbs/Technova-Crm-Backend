"""
Django admin registration for CRM models.
"""
from django.contrib import admin

from .models import (
    Lead, Milestone, Project, Proposal, ProposalMessage, Task,
    ClientProjectRequest, ProjectMessage
)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'status', 'start_date', 'target_end_date')
    list_filter = ('status',)
    search_fields = ('title', 'description', 'client__company_name')
    date_hierarchy = 'start_date'  # date drill-down navigation


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'due_date', 'is_completed')
    list_filter = ('is_completed',)
    search_fields = ('title', 'project__title')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'assignee', 'priority', 'status', 'due_date')
    list_filter = ('priority', 'status')
    search_fields = ('title', 'description')
    date_hierarchy = 'due_date'


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'company', 'status', 'source', 'desired_deadline', 'created_at')
    list_filter = ('status', 'source')
    search_fields = ('name', 'email', 'company')
    date_hierarchy = 'created_at'
    readonly_fields = ('converted_client',)  # set only by the conversion engine


class ProposalMessageInline(admin.TabularInline):
    """Inline messages so staff can read the negotiation thread inside the proposal."""
    model = ProposalMessage
    extra = 0
    readonly_fields = ('author', 'body', 'created_at')  # append-only thread


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'lead', 'status', 'proposed_budget', 'created_at')
    list_filter = ('status',)
    search_fields = ('title', 'scope', 'client__company_name')
    date_hierarchy = 'created_at'
    readonly_fields = ('linked_project',)  # set only by accept_proposal()
    inlines = [ProposalMessageInline]


@admin.register(ClientProjectRequest)
class ClientProjectRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'status', 'desired_deadline', 'created_at')
    list_filter = ('status',)
    search_fields = ('title', 'client__company_name')
    date_hierarchy = 'created_at'


@admin.register(ProjectMessage)
class ProjectMessageAdmin(admin.ModelAdmin):
    list_display = ('project', 'author', 'is_feature_request', 'created_at')
    list_filter = ('is_feature_request',)
    search_fields = ('project__title', 'body')
    date_hierarchy = 'created_at'
