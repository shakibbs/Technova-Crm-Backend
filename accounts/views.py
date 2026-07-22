"""
Auth + profile views for the accounts app.

JWT issuance (login) and rotation (refresh) come from simplejwt's built-in
views. We wrap them with a CookieTokenRefreshView so the refresh token can
travel via an HttpOnly cookie instead of the request body.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .permissions import IsAdmin
from .serializers import (
    ChangePasswordSerializer, ProfileUpdateSerializer, RegisterSerializer, UserSerializer,
)

User = get_user_model()


def _set_refresh_cookie(response):
    """Copy the refresh token from the JSON body into an HttpOnly cookie.

    simplejwt returns {access, refresh} in the response body. The frontend
    only stores the short-lived `access` token; the long-lived `refresh`
    token must live in an HttpOnly cookie so JavaScript (and XSS) can never
    read it. This makes silent refresh work (see CookieTokenRefreshView).
    """
    refresh = response.data.get('refresh')
    if refresh is None:
        return

    cookie_name = settings.SIMPLE_JWT.get('AUTH_COOKIE', 'refresh_token')
    response.set_cookie(
        cookie_name,
        refresh,
        max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
        httponly=settings.SIMPLE_JWT.get('AUTH_COOKIE_HTTP_ONLY', True),
        secure=settings.SIMPLE_JWT.get('AUTH_COOKIE_SECURE', not settings.DEBUG),
        samesite=settings.SIMPLE_JWT.get('AUTH_COOKIE_SAMESITE', 'Lax'),
        path=settings.SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/'),
    )
    # The refresh token must NOT remain in the JSON body.
    response.data.pop('refresh', None)


class LoginView(TokenObtainPairView):
    """
    Shared login endpoint (/api/v1/accounts/login/).

    Accepts {email, password}, returns the access JWT in the JSON body and
    stores the refresh JWT in an HttpOnly cookie. The frontend decodes the
    access token to read the user's role and route them to the dashboard.
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        _set_refresh_cookie(response)
        return response


class LogoutView(generics.GenericAPIView):
    """
    Logout endpoint (/api/v1/accounts/logout/).

    Deletes the HttpOnly refresh-token cookie. JWTs are stateless so we
    cannot revoke the access token here, but its short 15-minute lifetime
    bounds the exposure window. Pair with token rotation/blacklisting later
    if longer revocation guarantees are required.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        response = Response({'detail': 'Logged out.'}, status=status.HTTP_200_OK)
        response.delete_cookie(
            settings.SIMPLE_JWT.get('AUTH_COOKIE', 'refresh_token'),
            path=settings.SIMPLE_JWT.get('AUTH_COOKIE_PATH', '/'),
        )
        return response


class CookieTokenRefreshView(TokenRefreshView):
    """
    Refresh endpoint that reads the refresh token from the HttpOnly cookie
    set during login, so the frontend never has to handle it in JS.
    """
    def post(self, request, *args, **kwargs):
        # Fall back to the cookie if no token was sent in the body
        if 'refresh' not in request.data and request.COOKIES.get('refresh_token'):
            request.data['refresh'] = request.COOKIES.get('refresh_token')
        response = super().post(request, *args, **kwargs)
        return response


class MeView(generics.RetrieveUpdateAPIView):
    """
    Current user profile (/api/v1/auth/me/).

    GET  -> full user (with nested profile).
    PUT/PATCH -> update name + role-specific profile fields.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user  # the JWT identifies the user

    def get_serializer_class(self):
        # Use the writable serializer for updates, the read serializer for reads.
        if self.request.method in ('PUT', 'PATCH'):
            return ProfileUpdateSerializer
        return UserSerializer


class ChangePasswordView(generics.GenericAPIView):
    """Change the current user's password (/api/v1/auth/me/password/)."""
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'detail': 'Password updated successfully.'}, status=status.HTTP_200_OK)


class RegisterView(generics.CreateAPIView):
    """
    Create a new staff account (/api/v1/auth/register/).

    Admin-only: clients are created via the Lead conversion engine, not here.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [IsAdmin]
