"""
Public (anonymous) CRM routes (/api/v1/public/).

Only the lead intake is public here; everything else is protected.
Mounted by crm_project.api_urls.
"""
from django.urls import path

from .views import PublicLeadCreateView

urlpatterns = [
    path('leads/', PublicLeadCreateView.as_view(), name='public-lead-create'),
]
