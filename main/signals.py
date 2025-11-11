from __future__ import annotations

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Student, StudentPayment, Teacher
from .views import trigger_overview_warmup_async


def _schedule_overview_warmup() -> None:
    """Warm overview caches after the surrounding transaction commits."""

    transaction.on_commit(lambda: trigger_overview_warmup_async())


@receiver(post_save, sender=Student)
def refresh_overview_on_student_save(sender, instance, **kwargs):  # pragma: no cover
    _schedule_overview_warmup()


@receiver(post_delete, sender=Student)
def refresh_overview_on_student_delete(sender, instance, **kwargs):  # pragma: no cover
    _schedule_overview_warmup()


@receiver(post_save, sender=Teacher)
def refresh_overview_on_teacher_save(sender, instance, **kwargs):  # pragma: no cover
    _schedule_overview_warmup()


@receiver(post_delete, sender=Teacher)
def refresh_overview_on_teacher_delete(sender, instance, **kwargs):  # pragma: no cover
    _schedule_overview_warmup()


@receiver(post_save, sender=StudentPayment)
def refresh_overview_on_payment_save(sender, instance, **kwargs):  # pragma: no cover
    if instance.status != StudentPayment.Status.CONFIRMED:
        return
    _schedule_overview_warmup()


@receiver(post_delete, sender=StudentPayment)
def refresh_overview_on_payment_delete(sender, instance, **kwargs):  # pragma: no cover
    if instance.status != StudentPayment.Status.CONFIRMED:
        return
    _schedule_overview_warmup()
