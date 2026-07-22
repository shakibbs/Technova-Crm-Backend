"""
DRF serializers for the accounts app.

Serializers convert model instances <-> JSON and apply validation.
They are also where nested profile data (ClientProfile / EmployeeProfile)
is exposed alongside the core User fields.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import ClientProfile, EmployeeProfile

User = get_user_model()  # resolves to accounts.User via AUTH_USER_MODEL


class ClientProfileSerializer(serializers.ModelSerializer):
    """Read/write serializer for the ClientProfile (1:1 with User)."""

    class Meta:
        model = ClientProfile
        fields = ['company_name', 'industry', 'billing_address']


class EmployeeProfileSerializer(serializers.ModelSerializer):
    """Read/write serializer for the EmployeeProfile (1:1 with User)."""

    class Meta:
        model = EmployeeProfile
        fields = ['department', 'hire_date']


class UserSerializer(serializers.ModelSerializer):
    """Primary user serializer, with the matching profile nested inline."""

    # read_only nested profile -> returned with the user, set via signals/views
    client_profile = ClientProfileSerializer(read_only=True)
    employee_profile = EmployeeProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role',
            'client_profile', 'employee_profile',
        ]
        read_only_fields = ['id', 'role']  # role changes only via trusted flows


class RegisterSerializer(serializers.ModelSerializer):
    """
    Public staff-registration input serializer.

    Only used internally/admin-side to create employee/admin accounts.
    Client accounts are NOT created here; they are spawned by the
    Lead -> Client conversion engine (Phase 3).
    """
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'password2']

    def validate(self, attrs):
        # Ensure both password fields match before saving
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {'password2': 'Password fields did not match.'})
        return attrs

    def create(self, validated_data):
        # Drop the confirmation field, then create the user (password hashed by manager)
        validated_data.pop('password2')
        return User.objects.create_user(**validated_data)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Lets the logged-in user edit their name (+ company info for clients).

    Department is admin-managed, so employees cannot change it here.
    """

    client_profile = ClientProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'client_profile']
        extra_kwargs = {'email': {'required': False}}

    def update(self, instance, validated_data):
        instance.email = validated_data.get('email', instance.email)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.save()

        client_data = validated_data.get('client_profile')
        if client_data and getattr(instance, 'client_profile', None):
            for k, v in client_data.items():
                setattr(instance.client_profile, k, v)
            instance.client_profile.save()

        return instance


class ChangePasswordSerializer(serializers.Serializer):
    """Validates the current password and a strong new password."""

    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Your current password is incorrect.')
        return value
