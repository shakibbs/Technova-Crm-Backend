"""
Lead -> Client conversion engine.

This is the ONLY place a Lead becomes a real client account. The whole
operation is wrapped in a single DB transaction so it can never half-succeed
(if anything fails, every change rolls back -- SRS §4.1 integrity requirement).
"""
import secrets
import string

from django.db import transaction

from accounts.models import ClientProfile, User
from .models import Lead, Project, Proposal, ProposalMessage, Task
from .notify import send_client_credentials


def recalculate_project_status(project: Project) -> None:
    """
    Auto-sync a project's status from its tasks.

    Rules (only applied when the project is NOT on hold — on_hold is an
    admin-only manual lock and is never overridden automatically):
      * 0 tasks            -> Not Started
      * all tasks done     -> Completed
      * tasks, not all done -> In Progress
    """
    if project.status == Project.Status.ON_HOLD:
        return  # admin has locked the project; respect it

    tasks = project.tasks.all()
    total = tasks.count()

    if total == 0:
        new_status = Project.Status.NOT_STARTED
    elif all(t.status == Task.Status.DONE for t in tasks):
        new_status = Project.Status.COMPLETED
    else:
        new_status = Project.Status.IN_PROGRESS

    if project.status != new_status:
        project.status = new_status
        project.save(update_fields=['status', 'updated_at'])
        # Notify the client when the project transitions to Completed
        if new_status == Project.Status.COMPLETED:
            try:
                from .notify import notify_project_completed
                notify_project_completed(project)
            except Exception:
                pass  # email failure should not block the status update


def _generate_temp_password(length: int = 16) -> str:
    """Cryptographically-strong random one-time password."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@transaction.atomic  # all-or-nothing: User + ClientProfile + lead update
def convert_lead(lead: Lead) -> ClientProfile:
    """
    Turn a qualified Lead into a live client account.

    Steps:
      1. Reject if already converted (idempotency guard).
      2. Create User(role='client') with a random temp password.
      3. Create ClientProfile (1:1) copying name/company from the lead.
      4. Mark lead Converted + link it back to the new client.
      5. Email the client their temp credentials (see notify.py).

    Returns the new ClientProfile.
    """
    if lead.status == Lead.Status.CONVERTED:
        raise ValueError('Lead is already converted.')

    # 0) dedupe: if a client account already exists for this email, reuse it
    #    instead of creating a duplicate (same person can submit multiple leads).
    existing_user = User.objects.filter(
        email=lead.email, role=User.Role.CLIENT).first()
    if existing_user and existing_user.client_profile:
        client_profile = existing_user.client_profile
    else:
        temp_password = _generate_temp_password()

        # 1) create the auth account
        user = User.objects.create_user(
            email=lead.email,
            password=temp_password,
            first_name=lead.name.split(' ')[0] if lead.name else '',
            role=User.Role.CLIENT,
        )

        # 2) create the business profile linked 1:1
        client_profile = ClientProfile.objects.create(
            user=user,
            company_name=lead.company,
        )

        # 3) deliver credentials (sync now; Celery in Phase 6)
        send_client_credentials(user.email, temp_password,
                                recipient_name=lead.name or user.first_name)

    # 4) mark THIS lead + every duplicate lead (same email) as converted +
    #    linked to the same client, so no stray "unconverted" leads remain.
    Lead.objects.filter(email=lead.email).exclude(
        status=Lead.Status.LOST
    ).update(
        status=Lead.Status.CONVERTED,
        converted_client=client_profile,
    )

    return client_profile


@transaction.atomic  # all-or-nothing: status change + Project creation
def accept_proposal(proposal: Proposal) -> Project:
    """
    Accept the CURRENT figures on a proposal -> create the live Project.

    Called when a party accepts the proposal as-is (no counter-offer).
    Pre-fills the Project with the proposal's budget + timeline. Idempotent.
    """
    if proposal.linked_project_id is not None:
        return proposal.linked_project  # already accepted -> return existing

    project = Project.objects.create(
        title=proposal.title,
        description=proposal.scope,
        status=Project.Status.NOT_STARTED,
        client=proposal.client,
        start_date=proposal.proposed_start_date,
        target_end_date=proposal.proposed_end_date,
    )
    proposal.status = Proposal.Status.ACCEPTED
    proposal.linked_project = project
    proposal.save(update_fields=['status', 'linked_project'])
    # Send deal confirmation email to the client (non-blocking)
    try:
        from .notify import notify_deal_confirmed
        notify_deal_confirmed(proposal, project)
    except Exception:
        pass
    return project


@transaction.atomic  # all-or-nothing: counter-offer merge + Project creation
def accept_counter_offer(message: 'ProposalMessage') -> Project:
    """
    Accept a specific counter-offer -> merge its figures into the proposal,
    mark it ACCEPTED, and create the Project with those terms.

    The counter-offer's budget/timeline/scope overwrite the proposal's current
    values, so the project reflects the mutually agreed figures.
    """
    if message.message_type != ProposalMessage.MessageType.COUNTER_OFFER:
        raise ValueError('Only counter-offers can be accepted.')

    proposal = message.proposal

    # If proposal already finalized, just return the existing project
    if proposal.linked_project_id is not None:
        message.offer_status = ProposalMessage.OfferStatus.ACCEPTED
        message.save(update_fields=['offer_status'])
        return proposal.linked_project

    # Merge the accepted counter-offer's figures into the proposal
    if message.proposed_budget is not None:
        proposal.proposed_budget = message.proposed_budget
    if message.proposed_start_date is not None:
        proposal.proposed_start_date = message.proposed_start_date
    if message.proposed_end_date is not None:
        proposal.proposed_end_date = message.proposed_end_date
    if message.proposed_scope:
        proposal.scope = message.proposed_scope

    # Create the project with the finalized terms
    project = Project.objects.create(
        title=proposal.title,
        description=proposal.scope,
        status=Project.Status.NOT_STARTED,
        client=proposal.client,
        start_date=proposal.proposed_start_date,
        target_end_date=proposal.proposed_end_date,
    )
    proposal.status = Proposal.Status.ACCEPTED
    proposal.linked_project = project
    proposal.save()  # save all merged fields

    message.offer_status = ProposalMessage.OfferStatus.ACCEPTED
    message.save(update_fields=['offer_status'])
    # Send deal confirmation email to the client (non-blocking)
    try:
        from .notify import notify_deal_confirmed
        notify_deal_confirmed(proposal, project)
    except Exception:
        pass
    return project


@transaction.atomic
def reject_proposal(proposal: Proposal, rejected_by, reason: str):
    """
    Reject a proposal with a reason message.

    Creates a ProposalMessage (type=MESSAGE) recording who rejected and why,
    then sets the proposal status to REJECTED.
    """
    ProposalMessage.objects.create(
        proposal=proposal,
        author=rejected_by,
        body=reason,                       # rejection reason
        message_type=ProposalMessage.MessageType.MESSAGE,
    )
    proposal.status = Proposal.Status.REJECTED
    proposal.save(update_fields=['status'])
    return proposal
