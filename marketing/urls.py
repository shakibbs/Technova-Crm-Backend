"""
Marketing public URL routes (/api/v1/marketing/).

All endpoints are public (no auth) and read-only.
Content is managed by staff via the Django admin.
"""
from django.urls import path

from .views import (
    CaseStudyDetailView, CaseStudyListView,
    ServiceDetailView, ServiceListView,
    TeamMemberListView, TestimonialListView,
)

urlpatterns = [
    # Services
    path('services/', ServiceListView.as_view(), name='service-list'),
    path('services/<slug:slug>/', ServiceDetailView.as_view(), name='service-detail'),

    # Testimonials
    path('testimonials/', TestimonialListView.as_view(), name='testimonial-list'),

    # Case studies (portfolio)
    path('case-studies/', CaseStudyListView.as_view(), name='casestudy-list'),
    path('case-studies/<slug:slug>/', CaseStudyDetailView.as_view(), name='casestudy-detail'),

    # Team
    path('team/', TeamMemberListView.as_view(), name='team-list'),
]
