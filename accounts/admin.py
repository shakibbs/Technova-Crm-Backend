"""
Django admin registration for the accounts app.
Lets us manage users + profiles from /admin/ during development.
"""
from django.contrib import admin

from .models import ClientProfile, EmployeeProfile, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active')  # columns in list view
    list_filter = ('role', 'is_staff', 'is_active')   # sidebar filters
    search_fields = ('email', 'first_name', 'last_name')  # search box


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'industry')
    search_fields = ('company_name', 'industry', 'user__email')


@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'hire_date')
    search_fields = ('department', 'user__email')
