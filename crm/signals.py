"""
Signals that keep a project's status in sync with its tasks.

Whenever a Task is created, updated, or deleted we recompute the parent
project's status (see services.recalculate_project_status). On-hold projects
are an admin lock and are never auto-changed.
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from .models import Task
from .services import recalculate_project_status


@receiver(pre_save, sender=Task)
def _capture_old_project(sender, instance: Task, **kwargs):
    """Remember the previous project so we can recalc it if the task moves."""
    if instance.pk:
        try:
            instance._previous_project = Task.objects.values_list(
                'project_id', flat=True).get(pk=instance.pk)
        except Task.DoesNotExist:
            instance._previous_project = None
    else:
        instance._previous_project = None


@receiver(post_save, sender=Task)
def _task_saved(sender, instance: Task, created, **kwargs):
    recalculate_project_status(instance.project)
    prev = getattr(instance, '_previous_project', None)
    # If the task was moved to a different project, refresh the old one too.
    if prev and prev != instance.project_id:
        from .models import Project
        old_project = Project.objects.filter(pk=prev).first()
        if old_project:
            recalculate_project_status(old_project)


@receiver(post_delete, sender=Task)
def _task_deleted(sender, instance: Task, **kwargs):
    recalculate_project_status(instance.project)
