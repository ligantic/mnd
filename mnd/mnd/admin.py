from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from mnd.models import (
    DuplicatePatient,
    MIMSCMICache,
    MIMSProductCache,
    RegistrationConsent,
)


@admin.register(RegistrationConsent)
class RegistrationConsentAdmin(admin.ModelAdmin):
    list_display = ("patient", "accepted_at", "accepted_by", "language")
    readonly_fields = (
        "patient",
        "accepted_by",
        "accepted_at",
        "wording",
        "information_sheet",
        "language",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DuplicatePatientAdmin(admin.ModelAdmin):
    list_display = (
        "patient_link",
        "working_groups",
        "created_at",
        "created_by",
        "last_updated",
    )
    list_filter = ("is_duplicate",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(patient__active=True)

    def patient_link(self, obj):
        patient_url = reverse(
            "patient_edit",
            kwargs={
                "registry_code": obj.patient.rdrf_registry.first().code,
                "patient_id": obj.patient.id,
            },
        )
        return mark_safe(
            f"<a href='{patient_url}'>{obj.patient.display_name}</a>"
        )

    patient_link.short_description = "Patient"

    def working_groups(self, obj):
        return obj.patient.working_groups_display

    def created_at(self, obj):
        return obj.patient.created_at

    def created_by(self, obj):
        return obj.patient.created_by

    def last_updated(self, obj):
        return obj.patient.last_updated_overall_at


class MIMSProductCacheAdmin(admin.ModelAdmin):
    list_display = ("uuid", "data", "created", "updated")
    list_filter = ("uuid",)
    actions = ["delete_selected"]


class MIMSCMICacheAdmin(admin.ModelAdmin):
    list_display = ("uuid", "data", "created", "updated")
    list_filter = ("uuid",)
    actions = ["delete_selected"]


admin.site.register(DuplicatePatient, DuplicatePatientAdmin)
admin.site.register(MIMSProductCache, MIMSProductCacheAdmin)
admin.site.register(MIMSCMICache, MIMSCMICacheAdmin)
