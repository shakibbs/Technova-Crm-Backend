"""
Core CRM models: Project, Milestone, Task.

Design rules (from the architecture spec):
- UUID primary keys (shield table scale, prevent enumeration).
- ON DELETE RESTRICT for financially critical links (Project -> ClientProfile).
- ON DELETE CASCADE for transient children (Milestone/Task -> Project).
- DB indexes on status / lookup columns for fast filtering.
"""
import uuid

from django.conf import settings
from django.db import models

from accounts.models import ClientProfile


class TimeStampedModel(models.Model):
    """
    Abstract base shared by every CRM model.

    Provides a UUID primary key plus created/updated timestamps so we never
    repeat that boilerplate in each concrete model.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # non-sequential PK
    created_at = models.DateTimeField(auto_now_add=True)  # set once on insert
    updated_at = models.DateTimeField(auto_now=True)      # refreshed on every save

    class Meta:
        abstract = True  # Django won't create a table for this; subclasses inherit it


class Project(TimeStampedModel):
    """A delivery engagement tied to one client."""

    class Status(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not Started'
        IN_PROGRESS = 'in_progress', 'In Progress'
        ON_HOLD = 'on_hold', 'On Hold'
        COMPLETED = 'completed', 'Completed'

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.NOT_STARTED, db_index=True)  # indexed for dashboard filters
    client = models.ForeignKey(
        ClientProfile, on_delete=models.RESTRICT,  # never silently delete a billed client
        related_name='projects')
    start_date = models.DateField()
    target_end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']  # newest projects first by default

    def __str__(self):
        return self.title


class Milestone(TimeStampedModel):
    """A checkpoint within a project (with a due date + completion flag)."""

    title = models.CharField(max_length=255)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,  # milestone dies with its project
        related_name='milestones')
    due_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        ordering = ['due_date']  # chronological milestone order

    def __str__(self):
        return f'{self.title} ({self.project.title})'


class Task(TimeStampedModel):
    """A unit of work inside a project, assigned to an employee."""

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    class Status(models.TextChoices):
        TODO = 'todo', 'To Do'
        IN_PROGRESS = 'in_progress', 'In Progress'
        REVIEW = 'review', 'In Review'
        DONE = 'done', 'Done'

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='tasks')
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,  # keep the task if the employee leaves
        null=True, blank=True, related_name='tasks')
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM, db_index=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TODO, db_index=True)
    due_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-priority', 'due_date']  # urgent first, then by deadline

    def __str__(self):
        return self.title


class TaskUpdate(TimeStampedModel):
    """
    A threaded entry on a task — a progress report, an issue/blocker raised by
    the assigned employee, or a reply from an admin.

    This is the collaboration log for task delivery: the employee logs what they
    did / what's blocking them, and admins respond. Ordered newest-first so the
    latest activity appears at the top of the thread.
    """

    class Type(models.TextChoices):
        PROGRESS = 'progress', 'Progress Report'   # employee: what was done
        ISSUE = 'issue', 'Issue / Blocker'          # employee: something is blocking
        REPLY = 'reply', 'Reply'                    # admin: response to a report/issue

    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name='updates')   # task deleted -> updates go too
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,       # keep the entry if the user leaves
        null=True, blank=True, related_name='task_updates')
    update_type = models.CharField(
        max_length=15, choices=Type.choices, default=Type.PROGRESS)
    body = models.TextField()                    # the actual message / report

    class Meta:
        ordering = ['-created_at']               # newest updates first

    def __str__(self):
        return f'{self.get_update_type_display()} on {self.task}'


class Lead(TimeStampedModel):
    """
    A prospective client captured from the public website "Contact Us" form.

    This is the ONLY entry point for new clients: a Lead is reviewed by staff
    and, once qualified, converted (see crm/services.py) into a real
    User(role='client') + ClientProfile.
    """

    class Status(models.TextChoices):
        NEW = 'new', 'New'                       # just submitted via the website
        CONTACTED = 'contacted', 'Contacted'    # staff has reached out
        QUALIFIED = 'qualified', 'Qualified'    # verified as a real opportunity
        CONVERTED = 'converted', 'Converted'    # became a client account
        LOST = 'lost', 'Lost'                    # not pursued

    name = models.CharField(max_length=255)
    email = models.EmailField(db_index=True)     # indexed for lookup / dedupe
    phone = models.CharField(max_length=30, blank=True)
    company = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)       # the client's requirements (what they want)
    desired_deadline = models.DateField(null=True, blank=True)  # when the client needs it done
    source = models.CharField(max_length=100, default='website')  # where it came from
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.NEW, db_index=True)       # pipelines filter heavily by status
    captcha_verified = models.BooleanField(default=False)  # bot-mitigation outcome
    converted_client = models.ForeignKey(
        ClientProfile, on_delete=models.SET_NULL,  # keep the lead record for history
        null=True, blank=True, related_name='leads')

    class Meta:
        ordering = ['-created_at']  # newest leads first

    def __str__(self):
        return f'{self.name} <{self.email}>'


class Proposal(TimeStampedModel):
    """
    The commercial offer a staff member builds for a client.

    Flow: admin reviews a Lead's requirements (+ desired deadline), then
    creates this Proposal with the real budget, final timeline, scope and
    deliverables. It is sent to the client's portal; the client can only
    negotiate (via messages) and accept/reject -- never edit the figures.
    On acceptance, a Project is auto-created (see crm/services.py).
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'                # staff is still preparing it
        SENT = 'sent', 'Sent'                   # delivered to the client portal
        NEGOTIATING = 'negotiating', 'Negotiating'  # client requested changes
        ACCEPTED = 'accepted', 'Accepted'       # client approved -> project created
        REJECTED = 'rejected', 'Rejected'       # client declined

    client = models.ForeignKey(ClientProfile, on_delete=models.RESTRICT, related_name='proposals')
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='proposals')  # traceability to the originating lead
    title = models.CharField(max_length=255)
    scope = models.TextField()                  # deliverables / what will be built
    proposed_budget = models.DecimalField(max_digits=12, decimal_places=2)  # staff-set money
    proposed_start_date = models.DateField()
    proposed_end_date = models.DateField()      # final timeline (staff-set)
    technologies = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices,
                              default=Status.DRAFT, db_index=True)
    linked_project = models.ForeignKey(Project, on_delete=models.SET_NULL,
                                       null=True, blank=True, related_name='proposals')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Proposal: {self.title} ({self.client})'


class ProposalMessage(TimeStampedModel):
    """
    One entry in a proposal's negotiation thread.

    Three response options when receiving a proposal or counter-offer:
      1. ACCEPT   -> accept the current figures, project gets created
      2. REJECT   -> reject with a reason message (body field)
      3. NEGOTIATE -> send a counter-offer with new figures

    So a message can be:
      - MESSAGE       : plain text (e.g. a rejection reason or a question)
      - COUNTER_OFFER : carries the sender's proposed budget/timeline/scope

    Each counter-offer tracks its own resolution status so both parties can
    see the full back-and-forth history.
    """

    class MessageType(models.TextChoices):
        MESSAGE = 'message', 'Message'                    # plain text / rejection reason
        COUNTER_OFFER = 'counter_offer', 'Counter-offer'  # carries proposed figures

    class OfferStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'      # awaiting the other party's response
        ACCEPTED = 'accepted', 'Accepted'    # other party accepted -> proposal finalized
        REJECTED = 'rejected', 'Rejected'    # other party rejected
        SUPERSEDED = 'superseded', 'Superseded'  # a newer counter-offer replaced this one

    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='proposal_messages')
    body = models.TextField()                    # explanation / rejection reason / note
    message_type = models.CharField(max_length=20, choices=MessageType.choices,
                                    default=MessageType.MESSAGE, db_index=True)

    # Counter-offer fields (only set when message_type == COUNTER_OFFER)
    proposed_budget = models.DecimalField(max_digits=12, decimal_places=2,
                                          null=True, blank=True)
    proposed_start_date = models.DateField(null=True, blank=True)
    proposed_end_date = models.DateField(null=True, blank=True)
    proposed_scope = models.TextField(blank=True, default='')
    offer_status = models.CharField(max_length=20, choices=OfferStatus.choices,
                                    default=OfferStatus.PENDING)

    class Meta:
        ordering = ['created_at']  # conversation reads top-to-bottom

    def __str__(self):
        if self.message_type == self.MessageType.COUNTER_OFFER:
            return f'Counter-offer by {self.author} ({self.offer_status})'
        return f'Message by {self.author} on {self.proposal}'


class ClientProjectRequest(TimeStampedModel):
    """
    A request originated from an existing client via the client portal.
    Differs from Lead which is for new public users. Staff can review this
    and directly create a Proposal.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        REVIEWED = 'reviewed', 'Reviewed'
        PROPOSAL_SENT = 'proposal_sent', 'Proposal Sent'
        REJECTED = 'rejected', 'Rejected'

    client = models.ForeignKey(
        ClientProfile, on_delete=models.CASCADE, related_name='project_requests')
    title = models.CharField(max_length=255)
    description = models.TextField()
    desired_deadline = models.DateField(null=True, blank=True)
    proposed_budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.client})'


class ProjectMessage(TimeStampedModel):
    """
    Threaded message log for a specific Project, visible to both staff and client.
    Can be a regular message or a feature request.
    """
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='project_messages')
    body = models.TextField()
    is_feature_request = models.BooleanField(default=False, db_index=True)
    is_read_by_staff = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']  # chronological thread

    def __str__(self):
        return f'Message by {self.author} on {self.project}'
