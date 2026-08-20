"""
FacilityScopedPrimaryKeyRelatedField (TRD §8.1) — every writable
cross-object FK field in a facility-scoped API must use this, not a bare
`serializers.PrimaryKeyRelatedField`/ModelSerializer auto-field.

DRF's default PrimaryKeyRelatedField queryset is unscoped unless a view
remembers to validate the referenced object's facility by hand — several
of this codebase's ViewSets didn't (an audit found six across
patients/appointments/opd), which meant a user could create or update a
child record (an Allergy, a Vitals reading, a DoctorSchedule, ...)
pointing at a *different* facility's parent object and it would validate
successfully. This field closes that off at the one place every one of
those code paths passes through — `is_valid()` — instead of relying on
each view to re-implement the same `get_object_or_404(..., facility=...)`
check.
"""

from rest_framework import serializers

from apps.core.models import Department


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "facility", "name", "code", "parent_department"]
        read_only_fields = fields


class FacilityScopedPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def __init__(self, model, facility_lookup="facility", **kwargs):
        self.model = model
        self.facility_lookup = facility_lookup
        kwargs.setdefault("queryset", model.objects.none())
        super().__init__(**kwargs)

    def get_queryset(self):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return self.model.objects.none()
        return self.model.objects.filter(**{self.facility_lookup: request.user.facility})
