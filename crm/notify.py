"""
Notification wrapper (async seam).

Detects whether Celery + Redis are available:
  - If running (production): enqueues the email as a Celery task (non-blocking)
  - If not running (dev): sends synchronously via console backend

This means dev works without Redis, and production gets async email.
The callers (conversion service, views, signals) never change —
this is the only seam.
"""
from django.conf import settings


def _dispatch(task_name: str, args: list) -> None:
    """
    Dispatch a Celery task by dotted name, honoring CELERY_TASK_ALWAYS_EAGER.

    - False (default): queue the async task (production, non-blocking)
    - True: run synchronously in-process (dev without Redis)
    """
    from importlib import import_module
    module = import_module('crm.tasks')
    task_func = getattr(module, task_name)

    if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
        # Dev mode: run synchronously (prints to console with console backend)
        task_func.apply(args=args)
    else:
        # Production: enqueue as async task (non-blocking)
        task_func.delay(*args)


# ---------------------------------------------------------------------------
# Account credentials
# ---------------------------------------------------------------------------

def send_client_credentials(email: str, temp_password: str,
                            account_type: str = 'client',
                            recipient_name: str = '') -> None:
    """
    Deliver account credentials (client portal or employee CRM) + temp password.

    account_type: 'client' (default) or 'employee'.
    recipient_name: the user's display name, used in the email greeting.
    """
    _dispatch('send_credentials_email',
              [email, temp_password, account_type, recipient_name])


# ---------------------------------------------------------------------------
# Lifecycle notifications
# ---------------------------------------------------------------------------

def notify_proposal_sent(proposal) -> None:
    """Email the client when a proposal is sent to their portal."""
    client = proposal.client
    user = client.user
    name = f"{user.first_name}".strip() or client.company_name or "there"
    _dispatch('send_proposal_sent_email', [
        user.email,
        name,
        proposal.title,
        proposal.scope or '',
        f"${proposal.proposed_budget:,.2f}",
        str(proposal.proposed_start_date) if proposal.proposed_start_date else '',
        str(proposal.proposed_end_date) if proposal.proposed_end_date else '',
        proposal.technologies or '',
    ])


def notify_deal_confirmed(proposal, project) -> None:
    """Email the client when a proposal is accepted and a project is created."""
    client = proposal.client
    user = client.user
    name = f"{user.first_name}".strip() or client.company_name or "there"
    _dispatch('send_deal_confirmation_email', [
        user.email,
        name,
        proposal.title,
        project.title,
        f"${proposal.proposed_budget:,.2f}",
        str(proposal.proposed_start_date) if proposal.proposed_start_date else '',
        str(proposal.proposed_end_date) if proposal.proposed_end_date else '',
    ])


def notify_project_completed(project) -> None:
    """Email the client when a project transitions to COMPLETED."""
    client = project.client
    user = client.user
    name = f"{user.first_name}".strip() or client.company_name or "there"
    _dispatch('send_project_completed_email', [
        user.email,
        name,
        project.title,
    ])


def notify_task_assignment(task) -> None:
    """Email the assigned employee when a task is created or reassigned."""
    assignee = task.assignee
    if not assignee:
        return  # unassigned tasks don't notify
    name = f"{assignee.first_name} {assignee.last_name}".strip() or assignee.email
    _dispatch('send_task_assignment_email', [
        assignee.email,
        name,
        task.title,
        task.project.title,
        task.get_priority_display(),
        str(task.due_date) if task.due_date else '',
    ])
