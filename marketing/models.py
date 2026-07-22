"""
Marketing models for the public corporate website.

These power the dynamic content on the website:
  - Service     -> /services page (what the agency offers)
  - Testimonial -> social proof quotes on landing page
  - CaseStudy   -> /portfolio page (past project showcases)
  - TeamMember  -> about/team section

All models have `is_published` so staff can draft content before it goes live.
Public APIs only return published items; staff APIs show everything.
"""
from django.db import models


class PublishedModel(models.Model):
    """
    Abstract base for all marketing content.

    Provides:
      - is_published: draft vs live toggle (public API filters on this)
      - display_order: controls sort order on the website
      - created_at / updated_at: timestamps
    """
    is_published = models.BooleanField(default=False, db_index=True)  # draft vs live
    display_order = models.IntegerField(default=0)                     # sort weight
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['display_order', '-created_at']  # custom order, newest first


class Service(PublishedModel):
    """A service the agency offers (e.g. 'Web Development', 'Mobile Apps')."""

    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)    # URL-friendly identifier
    icon = models.CharField(max_length=50, blank=True)      # icon name for frontend
    short_description = models.CharField(max_length=255)    # card preview text
    full_description = models.TextField()                    # detail page body
    features = models.JSONField(default=list, blank=True)    # bullet points list

    def __str__(self):
        return self.title


class Testimonial(PublishedModel):
    """A client quote shown as social proof on the landing page."""

    client_name = models.CharField(max_length=120)
    client_title = models.CharField(max_length=120, blank=True)   # e.g. 'CEO, Acme Inc'
    company = models.CharField(max_length=120, blank=True)
    quote = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)           # 1-5 stars
    avatar_url = models.URLField(blank=True)                        # optional headshot

    def __str__(self):
        return f'{self.client_name} ({self.rating} stars)'


class CaseStudy(PublishedModel):
    """A portfolio piece showcasing past work (/portfolio page)."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    client_name = models.CharField(max_length=120, blank=True)     # optional NDA-friendly
    summary = models.CharField(max_length=500)                     # short card preview
    challenge = models.TextField()                                  # the problem
    solution = models.TextField()                                   # what we built
    results = models.TextField(blank=True)                          # outcome / metrics
    cover_image_url = models.URLField(blank=True)                   # hero image
    technologies = models.JSONField(default=list, blank=True)       # tech stack tags
    project_url = models.URLField(blank=True)                       # live link (optional)

    def __str__(self):
        return self.title


class TeamMember(PublishedModel):
    """A team member shown in the about/team section."""

    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120)                        # e.g. 'Lead Developer'
    bio = models.TextField(blank=True)
    photo_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)

    def __str__(self):
        return f'{self.name} - {self.role}'
