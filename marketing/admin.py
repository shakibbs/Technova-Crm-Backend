"""
Django admin for marketing content (staff manages website content here).
"""
from django.contrib import admin

from .models import CaseStudy, Service, TeamMember, Testimonial


class PublishedModelAdmin(admin.ModelAdmin):
    """Shared admin config for all marketing models."""
    list_display = ('__str__', 'is_published', 'display_order')
    list_filter = ('is_published',)
    list_editable = ('is_published', 'display_order')  # quick toggle in list view
    actions = ['publish_selected', 'unpublish_selected']

    @admin.action(description='Publish selected')
    def publish_selected(self, request, queryset):
        queryset.update(is_published=True)

    @admin.action(description='Unpublish selected')
    def unpublish_selected(self, request, queryset):
        queryset.update(is_published=False)


@admin.register(Service)
class ServiceAdmin(PublishedModelAdmin):
    search_fields = ('title', 'short_description')
    prepopulated_fields = {'slug': ('title',)}  # auto-fill slug from title


@admin.register(Testimonial)
class TestimonialAdmin(PublishedModelAdmin):
    search_fields = ('client_name', 'company')
    list_display = ('client_name', 'company', 'rating', 'is_published', 'display_order')


@admin.register(CaseStudy)
class CaseStudyAdmin(PublishedModelAdmin):
    search_fields = ('title', 'client_name')
    prepopulated_fields = {'slug': ('title',)}
    list_display = ('title', 'client_name', 'is_published', 'display_order')


@admin.register(TeamMember)
class TeamMemberAdmin(PublishedModelAdmin):
    search_fields = ('name', 'role')
    list_display = ('name', 'role', 'is_published', 'display_order')
