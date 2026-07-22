"""
Marketing serializers.

Public-facing (read-only) serializers for published website content.
Staff can use the same serializers for full CRUD in the admin area.
"""
from rest_framework import serializers

from .models import CaseStudy, Service, TeamMember, Testimonial


class ServiceSerializer(serializers.ModelSerializer):
    """Serializer for agency services (/services page)."""

    class Meta:
        model = Service
        fields = [
            'id', 'title', 'slug', 'icon', 'short_description',
            'full_description', 'features', 'display_order',
        ]


class TestimonialSerializer(serializers.ModelSerializer):
    """Serializer for client testimonials (landing page social proof)."""

    class Meta:
        model = Testimonial
        fields = [
            'id', 'client_name', 'client_title', 'company',
            'quote', 'rating', 'avatar_url',
        ]


class CaseStudySerializer(serializers.ModelSerializer):
    """Serializer for portfolio case studies (/portfolio page)."""

    class Meta:
        model = CaseStudy
        fields = [
            'id', 'title', 'slug', 'client_name', 'summary',
            'challenge', 'solution', 'results', 'cover_image_url',
            'technologies', 'project_url',
        ]


class TeamMemberSerializer(serializers.ModelSerializer):
    """Serializer for team member profiles (about/team section)."""

    class Meta:
        model = TeamMember
        fields = [
            'id', 'name', 'role', 'bio', 'photo_url',
            'linkedin_url', 'github_url',
        ]
