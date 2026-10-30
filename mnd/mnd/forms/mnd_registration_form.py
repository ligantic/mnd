import uuid

import pycountry
from django.forms import (
    BooleanField,
    CharField,
    ChoiceField,
    DateField,
    ValidationError,
)
from django.forms.widgets import CheckboxInput, RadioSelect, Select
from django.utils import timezone
from django.utils.translation import gettext as _
from rdrf.forms.registration_forms import (
    PatientRegistrationForm,
    RegistrationFormCaseInsensitiveCheck,
)
from registry.patients.models import ParentGuardian

from ..models import CarerRegistration, RegistrationConsent


class MNDRegistrationForm(PatientRegistrationForm):
    registration_consent_information_sheet = (
        RegistrationConsent.INFORMATION_SHEET
    )
    country_choices = [("", _("Country"))] + [
        (country.alpha_2, country.name)
        for country in sorted(pycountry.countries, key=lambda c: c.name)
    ]
    contact_field_names = (
        "phone_number",
        "country",
        "address",
        "suburb",
        "postcode",
        "state",
    )
    guardian_field_names = (
        "parent_guardian_first_name",
        "parent_guardian_last_name",
        "parent_guardian_phone",
        "parent_guardian_date_of_birth",
        "parent_guardian_gender",
        "parent_guardian_country",
        "parent_guardian_address",
        "parent_guardian_suburb",
        "parent_guardian_postcode",
        "parent_guardian_state",
    )
    optional_guardian_fields = (
        "parent_guardian_date_of_birth",
        "parent_guardian_gender",
        "parent_guardian_state",
    )

    phone_number = CharField(label=_("Phone Number"), max_length=30)
    country = ChoiceField(label=_("Country"), choices=country_choices)
    address = CharField(label=_("Street"), max_length=100)
    suburb = CharField(label=_("Suburb / Town"), max_length=100)
    postcode = CharField(label=_("Postcode"), max_length=50)
    state = ChoiceField(
        label=_("State / County / Province / Region"),
        required=False,
    )
    has_guardian = BooleanField(label=_("Add guardian details"), required=False)
    parent_guardian_first_name = CharField(
        label=_("Given Names"), max_length=30, required=False
    )
    parent_guardian_last_name = CharField(
        label=_("Surname"), max_length=50, required=False
    )
    parent_guardian_phone = CharField(
        label=_("Phone Number"), max_length=20, required=False
    )
    parent_guardian_date_of_birth = DateField(
        label=_("Date of Birth"), required=False
    )
    parent_guardian_gender = ChoiceField(
        label=_("Gender"),
        choices=ParentGuardian.GENDER_CHOICES,
        widget=RadioSelect,
        required=False,
    )
    parent_guardian_country = ChoiceField(
        label=_("Country"), choices=country_choices, required=False
    )
    parent_guardian_address = CharField(
        label=_("Street"), max_length=100, required=False
    )
    parent_guardian_suburb = CharField(
        label=_("Suburb / Town"), max_length=50, required=False
    )
    parent_guardian_postcode = CharField(
        label=_("Postcode"), max_length=20, required=False
    )
    parent_guardian_state = ChoiceField(
        label=_("State / County / Province / Region"),
        required=False,
    )
    registration_consent = BooleanField(
        label=RegistrationConsent.WORDING,
        error_messages={
            "required": _("Please give your consent to registration.")
        },
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        guardian_selected = self.fields["has_guardian"].clean(
            self["has_guardian"].value()
        )
        for name in self.guardian_field_names:
            self.fields[name].required = (
                guardian_selected and name not in self.optional_guardian_fields
            )
            if not guardian_selected and self.is_bound:
                self.fields[name].disabled = True
            if name not in self.optional_guardian_fields:
                self.fields[name].widget.attrs["data-required-guardian"] = (
                    "true"
                )
        for prefix in ("", "parent_guardian_"):
            country = self[f"{prefix}country"].value()
            subdivisions = (
                pycountry.subdivisions.get(country_code=country)
                if country in dict(self.country_choices) and country
                else []
            )
            self.fields[f"{prefix}state"].choices = [("", "---------")] + [
                (state.code, state.name)
                for state in sorted(subdivisions, key=lambda s: s.name)
            ]
        for field in self.fields.values():
            if isinstance(field.widget, CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, Select):
                field.widget.attrs["class"] = "form-select"
            elif not isinstance(field.widget, RadioSelect):
                field.widget.attrs["class"] = "form-control"
        self.fields["parent_guardian_date_of_birth"].widget.attrs[
            "placeholder"
        ] = _("YYYY-MM-DD")

    @property
    def contact_fields(self):
        return [self[name] for name in self.contact_field_names]

    @property
    def guardian_fields(self):
        return [self[name] for name in self.guardian_field_names]

    def clean_parent_guardian_date_of_birth(self):
        value = self.cleaned_data["parent_guardian_date_of_birth"]
        if value and value > timezone.localdate():
            raise ValidationError(_("Date of birth cannot be in the future."))
        return value


class MNDCarerRegistrationForm(RegistrationFormCaseInsensitiveCheck):
    placeholders = {
        "username": _("Username"),
        "password1": _("Password"),
        "password2": _("Repeat Password"),
        "token": _("Registration token"),
    }

    password_fields = ["password1", "password2"]

    token = CharField(required=True, min_length=36, max_length=36)
    registry_code = CharField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_fields()

    def setup_fields(self):
        for field in self.fields:
            self.fields[field].widget.attrs["class"] = "form-control"
            self.fields[field].widget.attrs["placeholder"] = (
                self.placeholders.get(field, "")
            )
            if field in self.password_fields:
                self.fields[field].widget.render_value = True

    def clean_token(self):
        token = self.cleaned_data["token"]
        try:
            uid_token = uuid.UUID(token)
        except ValueError:
            raise ValidationError(_("Invalid token format !"))
        return uid_token

    def clean(self):
        cleaned_data = super().clean()
        token = cleaned_data["token"]
        email = cleaned_data["email"]
        if not CarerRegistration.objects.filter(
            token=token,
            status=CarerRegistration.CREATED,
            carer_email__iexact=email,
            expires_on__gte=timezone.now(),
        ).exists():
            raise ValidationError(_("Invalid token !"))
        return cleaned_data
