"""
CRM URL routes (internal staff gateway).

A DRF DefaultRouter auto-generates the CRUD endpoints:
    /api/v1/crm/projects/        -> list + create
    /api/v1/crm/projects/<uuid>/ -> retrieve + update + delete
    ...same for milestones/ and tasks/
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ClientDetailView, ClientListView, EmployeeCreateView, EmployeeDetailView,
    EmployeeListView, LeadViewSet, MilestoneViewSet, ProjectViewSet,
    ProposalViewSet, TaskViewSet, ClientProjectRequestViewSet
)

router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'milestones', MilestoneViewSet, basename='milestone')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'leads', LeadViewSet, basename='lead')      # includes /convert/ action
router.register(r'proposals', ProposalViewSet, basename='proposal')  # /send/ + /accept/
router.register(r'project-requests', ClientProjectRequestViewSet, basename='project-request')

urlpatterns = [
    path('clients/', ClientListView.as_view(), name='client-list'),          # for create dropdowns
    path('clients/<int:pk>/', ClientDetailView.as_view(), name='client-detail'),  # full client profile
    path('employees/', EmployeeListView.as_view(), name='employee-list'),    # for task dropdowns + team page
    path('employees/create/', EmployeeCreateView.as_view(), name='employee-create'),  # admin creates employee
    path('employees/<int:pk>/', EmployeeDetailView.as_view(), name='employee-detail'), # admin edit/deactivate
    path('', include(router.urls)),  # mounts all registered CRUD routes
]
