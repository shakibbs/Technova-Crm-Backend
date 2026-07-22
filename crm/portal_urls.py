"""
Client-portal URL routes (/api/v1/portal/).

Mounted under the 'portal/' prefix in crm_project/api_urls.py.
Only authenticated clients (role='client') can access these endpoints.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .portal_views import PortalProjectViewSet, PortalProposalViewSet, ClientProjectRequestViewSet

router = DefaultRouter()
router.register(r'proposals', PortalProposalViewSet, basename='portal-proposal')
router.register(r'projects', PortalProjectViewSet, basename='portal-project')
router.register(r'project-requests', ClientProjectRequestViewSet, basename='portal-project-request')

urlpatterns = [
    path('', include(router.urls)),
]
