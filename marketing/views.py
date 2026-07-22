"""
Marketing public views (read-only, no authentication).

These endpoints serve published website content. Anyone can read them;
drafts (is_published=False) are invisible. Content is managed via the
Django admin interface by staff.

Each endpoint supports:
  - List   GET /marketing/services/            -> all published items
  - Detail GET /marketing/services/<slug>/      -> single item by slug
"""
from rest_framework import generics
from rest_framework.permissions import AllowAny

from .models import CaseStudy, Service, TeamMember, Testimonial
from .serializers import (
    CaseStudySerializer, ServiceSerializer,
    TeamMemberSerializer, TestimonialSerializer,
)


class ServiceListView(generics.ListAPIView):
    """GET /marketing/services/ -> list all published services."""
    queryset = Service.objects.filter(is_published=True)
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]
    throttle_classes = []  # public read-only content: exempt from anon throttle


class ServiceDetailView(generics.RetrieveAPIView):
    """GET /marketing/services/<slug>/ -> single published service."""
    queryset = Service.objects.filter(is_published=True)
    serializer_class = ServiceSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'                          # use slug instead of UUID
    throttle_classes = []  # public read-only content: exempt from anon throttle


class TestimonialListView(generics.ListAPIView):
    """GET /marketing/testimonials/ -> list all published testimonials."""
    queryset = Testimonial.objects.filter(is_published=True)
    serializer_class = TestimonialSerializer
    permission_classes = [AllowAny]
    throttle_classes = []  # public read-only content: exempt from anon throttle


class CaseStudyListView(generics.ListAPIView):
    """GET /marketing/case-studies/ -> list all published portfolio pieces."""
    queryset = CaseStudy.objects.filter(is_published=True)
    serializer_class = CaseStudySerializer
    permission_classes = [AllowAny]
    throttle_classes = []  # public read-only content: exempt from anon throttle


class CaseStudyDetailView(generics.RetrieveAPIView):
    """GET /marketing/case-studies/<slug>/ -> single published case study."""
    queryset = CaseStudy.objects.filter(is_published=True)
    serializer_class = CaseStudySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    throttle_classes = []  # public read-only content: exempt from anon throttle


class TeamMemberListView(generics.ListAPIView):
    """GET /marketing/team/ -> list all published team members."""
    queryset = TeamMember.objects.filter(is_published=True)
    serializer_class = TeamMemberSerializer
    permission_classes = [AllowAny]
    throttle_classes = []  # public read-only content: exempt from anon throttle
