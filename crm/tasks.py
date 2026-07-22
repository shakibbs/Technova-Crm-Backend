"""
Celery async tasks for the CRM app.

These run in a separate worker process, not in the HTTP request cycle.
The Celery worker is started with: celery -A crm_project worker -l info
"""
from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives


# ---------------------------------------------------------------------------
# Shared email template helpers
# ---------------------------------------------------------------------------

_BRAND = "TechNova"
_FRONTEND_BASE = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:5173")


def _full_name(recipient_name: str) -> str:
    """Return a clean display name, falling back to a generic greeting."""
    name = (recipient_name or "").strip()
    return name if name else "there"


def _html_wrapper(content_html: str, greeting: str, preheader: str = "") -> str:
    """
    Wrap an inner content block in a branded TechNova email shell.

    Provides a branded header bar, max-width 600px responsive table layout,
    and a standard footer — so individual emails only supply their body.
    """
    return f"""\
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="x-apple-disable-message-reformatting" />
  <title>{_BRAND}</title>
  <!--[if mso]>
  <noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript>
  <![endif]-->
  <style>
    body {{ margin:0; padding:0; background:#f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
    table {{ border-collapse:collapse; }}
    a {{ color:#6d28d9; text-decoration:none; }}
    .btn {{ display:inline-block; padding:12px 28px; background:#6d28d9; color:#ffffff !important; font-weight:600; border-radius:8px; }}
  </style>
</head>
<body>
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{preheader}</div>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:24px 12px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);">
          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#6d28d9 0%,#4f46e5 100%);padding:28px 32px;">
              <span style="font-size:22px;font-weight:700;color:#ffffff;letter-spacing:-0.5px;">{_BRAND}</span>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:32px;">
              <p style="margin:0 0 20px;font-size:16px;color:#1e293b;">{greeting}</p>
              {content_html}
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding:24px 32px;background:#f8fafc;border-top:1px solid #e2e8f0;">
              <p style="margin:0;font-size:13px;color:#64748b;line-height:1.5;">
                <strong style="color:#475569;">{_BRAND}</strong> — Delivering tomorrow's technology, today.<br />
                This is an automated message. Please do not reply directly to this email.
              </p>
            </td>
          </tr>
        </table>
        <p style="margin:16px 0 0;font-size:12px;color:#94a3b8;">&copy; {_BRAND}. All rights reserved.</p>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _send_dual(
    subject: str,
    text_body: str,
    html_body: str,
    to_email: str,
    preheader: str = "",
) -> None:
    """Send an email with both plain-text and HTML alternatives."""
    msg = EmailMultiAlternatives(
        subject=f"[{_BRAND}] {subject}",
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
    )
    msg.attach_alternative(_html_wrapper(html_body, "", preheader), "text/html")
    msg.send(fail_silently=False)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_credentials_email(self, email, temp_password, account_type='client',
                           recipient_name=''):
    """
    Async task: send account credentials email (client portal or employee CRM).

    account_type: 'client' -> portal login URL, 'employee' -> shared login URL.
    recipient_name: the user's display name for the greeting.
    Retries up to 3 times with 60-second delay if the mail server is down.
    Called from crm/notify.py instead of blocking the HTTP request.
    """
    name = _full_name(recipient_name)
    login_url = f"{_FRONTEND_BASE}/login"
    is_employee = account_type == 'employee'

    if is_employee:
        subject = "Welcome to the TechNova Team — Your CRM Account"
        role_heading = "You've been added as a team member"
        role_text = (
            "We're excited to have you on board! Your staff account for the "
            "TechNova CRM is ready. Below are your login details — please "
            "sign in and set a new password at your earliest convenience."
        )
    else:
        subject = "Your TechNova Client Portal Account is Ready"
        role_heading = "Your client portal account has been created"
        role_text = (
            "Welcome to TechNova! We're thrilled to begin working with you. "
            "Your personal client portal account is now active, giving you "
            "real-time access to your projects, proposals, and milestones. "
            "Use the credentials below to sign in."
        )

    greeting = f"Dear {name},"

    # Plain-text version
    text_body = (
        f"{greeting}\n\n"
        f"{role_text}\n\n"
        f"Login Email: {email}\n"
        f"Temporary Password: {temp_password}\n\n"
        f"For security, please change your password after your first login.\n\n"
        f"Log in here: {login_url}\n\n"
        f"Best regards,\nThe TechNova Team\n"
    )

    # HTML version
    html_body = f"""
      <p style="margin:0 0 16px;font-size:15px;color:#475569;line-height:1.6;">
        {role_text}
      </p>
      <p style="margin:0 0 8px;font-size:13px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;">
        {role_heading}
      </p>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;">
        <tr>
          <td style="padding:16px 20px;">
            <p style="margin:0 0 8px;font-size:14px;color:#64748b;">Login Email</p>
            <p style="margin:0 0 16px;font-size:15px;font-weight:600;color:#1e293b;">{email}</p>
            <p style="margin:0 0 8px;font-size:14px;color:#64748b;">Temporary Password</p>
            <p style="margin:0;font-size:15px;font-weight:600;color:#1e293b;font-family:monospace;letter-spacing:1px;">{temp_password}</p>
          </td>
        </tr>
      </table>
      <p style="margin:0 0 24px;font-size:14px;color:#64748b;">
        &#9888; For security, please change your password after your first login.
      </p>
      <a href="{login_url}" class="btn">Sign In Now</a>
      <p style="margin:16px 0 0;font-size:13px;color:#94a3b8;">
        If the button doesn't work, copy this link: {login_url}
      </p>
      <p style="margin:24px 0 0;font-size:15px;color:#1e293b;">
        Best regards,<br /><strong>The {_BRAND} Team</strong>
      </p>
    """

    try:
        _send_dual(
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            to_email=email,
            preheader=role_heading,
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_lead_notification(self, lead_id):
    """
    Async task: notify staff when a new lead arrives via the public form.

    Sends a professional email to the configured staff inbox
    (EMAIL_HOST_USER) with the lead's details so the team can
    follow up promptly.
    """
    try:
        from .models import Lead
        lead = Lead.objects.get(id=lead_id)

        subject = f"New Lead: {lead.name} — {lead.company or 'No company'}"
        crm_url = f"{_FRONTEND_BASE}/admin/leads"

        greeting = "Dear TechNova Team,"

        # Plain-text version
        text_body = (
            f"{greeting}\n\n"
            f"A new lead has just been submitted through our website. "
            f"Here are the details — please follow up as soon as possible.\n\n"
            f"Name:          {lead.name}\n"
            f"Email:         {lead.email}\n"
            f"Phone:         {lead.phone or 'N/A'}\n"
            f"Company:       {lead.company or 'N/A'}\n"
            f"Message:       {lead.message or 'N/A'}\n"
            f"Desired Deadline: {lead.desired_deadline or 'Not specified'}\n\n"
            f"Review and manage this lead in the CRM: {crm_url}\n\n"
            f"Best regards,\n{_BRAND} CRM\n"
        )

        # HTML version
        html_body = f"""
          <p style="margin:0 0 16px;font-size:15px;color:#475569;line-height:1.6;">
            A new lead has just been submitted through our website. Please review
            the details below and follow up as soon as possible.
          </p>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
            <tr><td style="padding:8px 0;font-size:14px;color:#64748b;width:160px;vertical-align:top;">Name</td><td style="padding:8px 0;font-size:15px;color:#1e293b;font-weight:600;">{lead.name}</td></tr>
            <tr><td style="padding:8px 0;font-size:14px;color:#64748b;border-top:1px solid #f1f5f9;vertical-align:top;">Email</td><td style="padding:8px 0;font-size:15px;color:#1e293b;border-top:1px solid #f1f5f9;"><a href="mailto:{lead.email}">{lead.email}</a></td></tr>
            <tr><td style="padding:8px 0;font-size:14px;color:#64748b;border-top:1px solid #f1f5f9;vertical-align:top;">Phone</td><td style="padding:8px 0;font-size:15px;color:#1e293b;border-top:1px solid #f1f5f9;">{lead.phone or 'N/A'}</td></tr>
            <tr><td style="padding:8px 0;font-size:14px;color:#64748b;border-top:1px solid #f1f5f9;vertical-align:top;">Company</td><td style="padding:8px 0;font-size:15px;color:#1e293b;border-top:1px solid #f1f5f9;">{lead.company or 'N/A'}</td></tr>
            <tr><td style="padding:8px 0;font-size:14px;color:#64748b;border-top:1px solid #f1f5f9;vertical-align:top;">Desired Deadline</td><td style="padding:8px 0;font-size:15px;color:#1e293b;border-top:1px solid #f1f5f9;">{lead.desired_deadline or 'Not specified'}</td></tr>
          </table>
          <p style="margin:0 0 8px;font-size:13px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;">Message</p>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
            <tr><td style="padding:16px 20px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;font-size:14px;color:#475569;line-height:1.6;">{lead.message or 'N/A'}</td></tr>
          </table>
          <a href="{crm_url}" class="btn">Review in CRM</a>
          <p style="margin:24px 0 0;font-size:15px;color:#1e293b;">
            Best regards,<br /><strong>{_BRAND} CRM</strong>
          </p>
        """

        _send_dual(
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            to_email=settings.EMAIL_HOST_USER,
            preheader=f"New inquiry from {lead.name}",
        )
    except Exception as exc:
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------
# Lifecycle notification tasks
# ---------------------------------------------------------------------------

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_proposal_sent_email(self, client_email, client_name, proposal_title,
                             scope, budget, start_date, end_date, technologies):
    """
    Notify a client that a proposal has been sent to their portal.

    Triggered by ProposalViewSet.send() — the client receives a professional
    email with the full proposal details prompting them to review and
    accept/negotiate.
    """
    name = _full_name(client_name)
    portal_url = f"{_FRONTEND_BASE}/portal/proposals"
    greeting = f"Dear {name},"
    scope_display = scope or 'Not specified'
    tech_display = technologies or 'Not specified'

    text_body = (
        f"{greeting}\n\n"
        f"We're pleased to share a new proposal for your review: "
        f'"{proposal_title}"\n\n'
        f"Scope / Deliverables:\n{scope_display}\n\n"
        f"Proposed Budget: {budget}\n"
        f"Proposed Start:  {start_date or 'TBD'}\n"
        f"Proposed End:    {end_date or 'TBD'}\n"
        f"Technologies:    {tech_display}\n\n"
        f"You can review the full details, negotiate terms, or accept the "
        f"proposal directly in your client portal.\n\n"
        f"View your proposal: {portal_url}\n\n"
        f"Best regards,\nThe {_BRAND} Team\n"
    )

    html_body = f"""
      <p style="margin:0 0 16px;font-size:15px;color:#475569;line-height:1.6;">
        We're pleased to share a new proposal for your review. Below are the
        full details &mdash; please log in to your portal to accept or
        request changes.
      </p>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
        <tr><td style="padding:8px 0;font-size:14px;color:#64748b;width:160px;vertical-align:top;">Proposal</td><td style="padding:8px 0;font-size:15px;color:#1e293b;font-weight:600;">{proposal_title}</td></tr>
        <tr><td style="padding:8px 0;font-size:14px;color:#64748b;border-top:1px solid #f1f5f9;vertical-align:top;">Proposed Budget</td><td style="padding:8px 0;font-size:15px;color:#1e293b;border-top:1px solid #f1f5f9;font-weight:600;">{budget}</td></tr>
        <tr><td style="padding:8px 0;font-size:14px;color:#64748b;border-top:1px solid #f1f5f9;vertical-align:top;">Start Date</td><td style="padding:8px 0;font-size:15px;color:#1e293b;border-top:1px solid #f1f5f9;">{start_date or 'TBD'}</td></tr>
        <tr><td style="padding:8px 0;font-size:14px;color:#64748b;border-top:1px solid #f1f5f9;vertical-align:top;">End Date</td><td style="padding:8px 0;font-size:15px;color:#1e293b;border-top:1px solid #f1f5f9;">{end_date or 'TBD'}</td></tr>
        <tr><td style="padding:8px 0;font-size:14px;color:#64748b;border-top:1px solid #f1f5f9;vertical-align:top;">Technologies</td><td style="padding:8px 0;font-size:15px;color:#1e293b;border-top:1px solid #f1f5f9;">{tech_display}</td></tr>
      </table>
      <p style="margin:0 0 8px;font-size:13px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:0.5px;">Scope & Deliverables</p>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
        <tr><td style="padding:16px 20px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;font-size:14px;color:#475569;line-height:1.6;">{scope_display}</td></tr>
      </table>
      <a href="{portal_url}" class="btn">Review Proposal</a>
      <p style="margin:24px 0 0;font-size:15px;color:#1e293b;">
        Best regards,<br /><strong>The {_BRAND} Team</strong>
      </p>
    """

    try:
        _send_dual(
            subject=f"New Proposal Ready for Review: {proposal_title}",
            text_body=text_body,
            html_body=html_body,
            to_email=client_email,
            preheader=f"Proposal: {proposal_title}",
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_project_completed_email(self, client_email, client_name, project_title):
    """
    Notify a client that their project has been completed.

    Triggered when recalculate_project_status() transitions a project to
    COMPLETED — the client receives a celebratory wrap-up email.
    """
    name = _full_name(client_name)
    portal_url = f"{_FRONTEND_BASE}/portal/projects"
    greeting = f"Dear {name},"

    text_body = (
        f"{greeting}\n\n"
        f"Great news! Your project \"{project_title}\" has been marked as "
        f"completed. All tasks have been finished and delivered.\n\n"
        f"You can view the full project history and final deliverables in "
        f"your client portal: {portal_url}\n\n"
        f"It's been a pleasure working with you. We'd love to hear your "
        f"feedback!\n\n"
        f"Best regards,\nThe {_BRAND} Team\n"
    )

    html_body = f"""
      <p style="margin:0 0 16px;font-size:15px;color:#475569;line-height:1.6;">
        Great news! We've successfully completed your project
        <strong style="color:#1e293b;">&ldquo;{project_title}&rdquo;</strong>.
        All tasks have been finished and delivered to your satisfaction.
      </p>
      <p style="margin:0 0 24px;font-size:15px;color:#475569;line-height:1.6;">
        You can review the full project history and milestones in your client
        portal. We'd also love to hear your feedback &mdash; it helps us
        continuously improve.
      </p>
      <a href="{portal_url}" class="btn">View Project</a>
      <p style="margin:24px 0 0;font-size:15px;color:#1e293b;">
        It's been a pleasure working with you!<br /><br />
        Best regards,<br /><strong>The {_BRAND} Team</strong>
      </p>
    """

    try:
        _send_dual(
            subject=f"Project Completed: {project_title}",
            text_body=text_body,
            html_body=html_body,
            to_email=client_email,
            preheader=f"Your project is complete!",
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_task_assignment_email(self, employee_email, employee_name, task_title,
                               project_title, priority, due_date):
    """
    Notify an employee that a new task has been assigned to them.

    Triggered by TaskViewSet when a task is created or reassigned.
    """
    name = _full_name(employee_name)
    crm_url = f"{_FRONTEND_BASE}/admin/tasks"
    greeting = f"Dear {name},"

    text_body = (
        f"{greeting}\n\n"
        f"You have been assigned a new task: \"{task_title}\"\n\n"
        f"Project:   {project_title}\n"
        f"Priority:  {priority}\n"
        f"Due Date:  {due_date or 'Not set'}\n\n"
        f"Please review the task details and update its status as you "
        f"progress. Access it in the CRM: {crm_url}\n\n"
        f"Best regards,\n{_BRAND} CRM\n"
    )

    html_body = f"""
      <p style="margin:0 0 16px;font-size:15px;color:#475569;line-height:1.6;">
        A new task has been assigned to you. Please review the details below
        and update its status as you make progress.
      </p>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
        <tr><td style="padding:8px 0;font-size:14px;color:#64748b;width:120px;vertical-align:top;">Task</td><td style="padding:8px 0;font-size:15px;color:#1e293b;font-weight:600;">{task_title}</td></tr>
        <tr><td style="padding:8px 0;font-size:14px;color:#64748b;border-top:1px solid #f1f5f9;vertical-align:top;">Project</td><td style="padding:8px 0;font-size:15px;color:#1e293b;border-top:1px solid #f1f5f9;">{project_title}</td></tr>
        <tr><td style="padding:8px 0;font-size:14px;color:#64748b;border-top:1px solid #f1f5f9;vertical-align:top;">Priority</td><td style="padding:8px 0;font-size:15px;color:#1e293b;border-top:1px solid #f1f5f9;">{priority}</td></tr>
        <tr><td style="padding:8px 0;font-size:14px;color:#64748b;border-top:1px solid #f1f5f9;vertical-align:top;">Due Date</td><td style="padding:8px 0;font-size:15px;color:#1e293b;border-top:1px solid #f1f5f9;">{due_date or 'Not set'}</td></tr>
      </table>
      <a href="{crm_url}" class="btn">Go to Tasks</a>
      <p style="margin:24px 0 0;font-size:15px;color:#1e293b;">
        Best regards,<br /><strong>{_BRAND} CRM</strong>
      </p>
    """

    try:
        _send_dual(
            subject=f"New Task Assigned: {task_title}",
            text_body=text_body,
            html_body=html_body,
            to_email=employee_email,
            preheader=f"New task: {task_title}",
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_deal_confirmation_email(self, client_email, client_name, proposal_title,
                                 project_title, budget, start_date, end_date):
    """
    Send a deal confirmation email when a proposal is accepted.

    Triggered by accept_proposal() / accept_counter_offer() in services.py
    once the project has been created — the client receives a celebratory
    confirmation that the deal is closed and the project is underway.
    """
    name = _full_name(client_name)
    portal_url = f"{_FRONTEND_BASE}/portal/projects"
    greeting = f"Dear {name},"

    text_body = (
        f"{greeting}\n\n"
        f'Congratulations! Your proposal "{proposal_title}" has been '
        f"accepted and we're excited to begin working together.\n\n"
        f"Project:         {project_title}\n"
        f"Agreed Budget:   {budget}\n"
        f"Start Date:      {start_date or 'TBD'}\n"
        f"Target End Date: {end_date or 'TBD'}\n\n"
        f"A new project has been created in your portal. You'll be able to "
        f"track milestones, tasks, and deliverables in real time as we "
        f"progress.\n\n"
        f"View your project: {portal_url}\n\n"
        f"We look forward to delivering outstanding results!\n\n"
        f"Best regards,\nThe {_BRAND} Team\n"
    )

    html_body = f"""
      <p style="margin:0 0 16px;font-size:15px;color:#475569;line-height:1.6;">
        Congratulations! Your proposal has been accepted and we're excited to
        begin working together. A new project has been created and is now
        active in your client portal.
      </p>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
        <tr><td style="padding:8px 0;font-size:14px;color:#64748b;width:160px;vertical-align:top;">Project</td><td style="padding:8px 0;font-size:15px;color:#1e293b;font-weight:600;">{project_title}</td></tr>
        <tr><td style="padding:8px 0;font-size:14px;color:#64748b;border-top:1px solid #f1f5f9;vertical-align:top;">Agreed Budget</td><td style="padding:8px 0;font-size:15px;color:#1e293b;border-top:1px solid #f1f5f9;font-weight:600;">{budget}</td></tr>
        <tr><td style="padding:8px 0;font-size:14px;color:#64748b;border-top:1px solid #f1f5f9;vertical-align:top;">Start Date</td><td style="padding:8px 0;font-size:15px;color:#1e293b;border-top:1px solid #f1f5f9;">{start_date or 'TBD'}</td></tr>
        <tr><td style="padding:8px 0;font-size:14px;color:#64748b;border-top:1px solid #f1f5f9;vertical-align:top;">Target End Date</td><td style="padding:8px 0;font-size:15px;color:#1e293b;border-top:1px solid #f1f5f9;">{end_date or 'TBD'}</td></tr>
      </table>
      <p style="margin:0 0 24px;font-size:15px;color:#475569;line-height:1.6;">
        You'll be able to track milestones, tasks, and deliverables in real
        time as we progress. If you have any questions, don't hesitate to
        reach out.
      </p>
      <a href="{portal_url}" class="btn">View Your Project</a>
      <p style="margin:24px 0 0;font-size:15px;color:#1e293b;">
        We look forward to delivering outstanding results!<br /><br />
        Best regards,<br /><strong>The {_BRAND} Team</strong>
      </p>
    """

    try:
        _send_dual(
            subject=f"Deal Confirmed: {proposal_title}",
            text_body=text_body,
            html_body=html_body,
            to_email=client_email,
            preheader="Your proposal has been accepted!",
        )
    except Exception as exc:
        raise self.retry(exc=exc)
