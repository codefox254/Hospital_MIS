"""
Core / shared models: Facility, Department, and the abstract base classes
every other module's models build on (TRD §4.1, §8.1; Data Dictionary §2).
"""

import uuid

from django.conf import settings
from django.db import models

from apps.core.mixins import AuditableModel


class UUIDModel(models.Model):
    """UUID primary key — avoids record enumeration across facilities (TRD §8.1)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Standard audit columns present on every core table (Data Dictionary §1.1)."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        abstract = True


class Facility(UUIDModel, TimeStampedModel):
    class FacilityType(models.TextChoices):
        CLINIC = "clinic", "Clinic"
        HOSPITAL = "hospital", "Hospital"
        BRANCH = "branch", "Branch"

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, unique=True)
    type = models.CharField(max_length=20, choices=FacilityType.choices)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "facilities"

    def __str__(self):
        return f"{self.name} ({self.code})"


class FacilityScopedManager(models.Manager):
    """
    Query-layer facility scoping (TRD §8.1): the intended access path for any
    facility-scoped queryset is `.for_facility(facility)`, so scoping is never
    left to individual view logic to remember. Base `.all()`/`.filter()`
    remain available for admin/reporting contexts that deliberately need a
    cross-facility view (e.g. the read-replica analytics layer, §8.1).
    """

    def for_facility(self, facility):
        return self.get_queryset().filter(facility=facility)


class FacilityScopedModel(UUIDModel, TimeStampedModel):
    """Abstract base for every module's facility-scoped tables (TRD §2, §8.1)."""

    facility = models.ForeignKey(Facility, on_delete=models.PROTECT, related_name="+")

    objects = FacilityScopedManager()

    class Meta:
        abstract = True


class Department(FacilityScopedModel, AuditableModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    parent_department = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sub_departments",
    )

    class Meta:
        ordering = ["facility", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["facility", "code"], name="unique_department_code_per_facility"
            ),
        ]

    def __str__(self):
        return f"{self.name} — {self.facility.code}"
