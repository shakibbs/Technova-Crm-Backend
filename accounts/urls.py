"""
URL routes for the accounts app (auth gateway).

Mounted under /api/v1/accounts/ by crm_project.api_urls.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView

from .views import (
    ChangePasswordView,
    CookieTokenRefreshView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='token_login'),                    # POST -> access + refresh cookie
    path('logout/', LogoutView.as_view(), name='token_logout'),                 # POST -> delete refresh cookie
    path('refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),   # POST -> new access (reads cookie)
    path('verify/', TokenVerifyView.as_view(), name='token_verify'),            # POST -> validate token
    path('me/', MeView.as_view(), name='me'),                                   # GET/PUT/PATCH -> current user
    path('me/password/', ChangePasswordView.as_view(), name='change-password'), # POST -> change password
    path('register/', RegisterView.as_view(), name='register'),                 # POST -> create staff (admin only)
]
