from datetime import timedelta
from unittest.mock import patch

from django.contrib import admin
from django.core import mail
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ModelState
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from lxml import html
from rdrf.events.events import EventType
from rdrf.models.definition.models import (
    ConsentQuestion,
    ConsentSection,
    EmailNotification,
    EmailTemplate,
    Registry,
)
from registration.models import RegistrationProfile
from registry.groups import GROUPS
from registry.groups.models import CustomUser
from registry.patients.admin_forms import ParentGuardianForm
from registry.patients.constants import PatientState
from registry.patients.models import (
    ConsentValue,
    ParentGuardian,
    Patient,
    PatientAddress,
    PatientStage,
    PatientStageRule,
)

from mnd.forms.mnd_registration_form import (
    MNDCarerRegistrationForm,
    MNDRegistrationForm,
)
from mnd.models import RegistrationConsent


class RegistrationTests(TestCase):
    databases = {"default", "clinical"}

    @classmethod
    def setUpTestData(cls):
        cls.registry = Registry.objects.create(
            code="mnd",
            name="MiNDAUS Registry",
            metadata_json='{"features": ["registration", "stages"]}',
        )
        template = EmailTemplate.objects.create(
            language="en",
            description="Registration",
            subject="Welcome",
            body="Please activate: {{ activation_url }}",
        )
        notification = EmailNotification.objects.create(
            registry=cls.registry,
            description=EventType.NEW_PATIENT_USER_REGISTERED,
            recipient="{{ patient.user.email }}",
            email_from="registry@example.org",
        )
        notification.email_templates.add(template)
        cls.consent_section = ConsentSection.objects.create(
            registry=cls.registry,
            code="participation",
            section_label="Participation",
            validation_rule="required",
        )
        cls.consent_question = ConsentQuestion.objects.create(
            section=cls.consent_section,
            code="required",
            position=1,
        )
        cls.stage, _ = PatientStage.objects.get_or_create(
            registry=cls.registry,
            name="Informed Consent",
        )
        PatientStageRule.objects.get_or_create(
            registry=cls.registry,
            from_stage=None,
            condition=PatientState.REGISTERED,
            to_stage=cls.stage,
            order=1,
        )
        cls.url = reverse(
            "registration_register", kwargs={"registry_code": "mnd"}
        )

    def data(self, guardian=False):
        data = {
            "registry_code": "mnd",
            "username": "patient@example.org",
            "email": "patient@example.org",
            "password1": "Uncommon-Registration-Password-42!",
            "password2": "Uncommon-Registration-Password-42!",
            "first_name": "Patient",
            "surname": "Example",
            "date_of_birth": "1970-01-02",
            "gender": "1",
            "preferred_languages": "en",
            "phone_number": "+61 400 123 456",
            "country": "AU",
            "address": "123 Example Street",
            "suburb": "Brisbane",
            "state": "AU-QLD",
            "postcode": "4000",
            "registration_consent": "on",
        }
        if guardian:
            data.update(
                {
                    "has_guardian": "on",
                    "parent_guardian_first_name": "Guardian",
                    "parent_guardian_last_name": "Example",
                    "parent_guardian_phone": "+61 400 654 321",
                    "parent_guardian_country": "AU",
                    "parent_guardian_address": "456 Other Street",
                    "parent_guardian_suburb": "Sydney",
                    "parent_guardian_state": "AU-NSW",
                    "parent_guardian_postcode": "2000",
                }
            )
        return data

    def post(self, data=None, recaptcha=True):
        with patch(
            "rdrf.views.registration_rdrf.RdrfRegistrationView.is_recaptcha_valid",
            return_value=recaptcha,
        ):
            return self.client.post(
                self.url,
                self.data() if data is None else data,
            )

    def test_patient_contact_fields_are_required_server_side(self):
        for field in (
            "phone_number",
            "country",
            "address",
            "suburb",
            "postcode",
        ):
            with self.subTest(field=field):
                data = self.data()
                data.pop(field)
                response = self.post(data)
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context["form"].errors)
        self.assertFalse(CustomUser.objects.exists())
        self.assertFalse(Patient.objects.exists())

    def test_blank_or_whitespace_contact_fields_are_rejected(self):
        for field in ("phone_number", "address", "suburb", "postcode"):
            with self.subTest(field=field):
                data = self.data()
                data[field] = "   "
                form = MNDRegistrationForm(data)
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_contact_and_guardian_lengths_match_storage(self):
        for guardian, field, limit in (
            (False, "phone_number", 30),
            (False, "postcode", 50),
            (True, "parent_guardian_first_name", 30),
            (True, "parent_guardian_last_name", 50),
            (True, "parent_guardian_phone", 20),
            (True, "parent_guardian_suburb", 50),
            (True, "parent_guardian_postcode", 20),
        ):
            with self.subTest(field=field):
                data = self.data(guardian=guardian)
                data[field] = "x" * limit
                self.assertTrue(MNDRegistrationForm(data).is_valid())
                data[field] += "x"
                form = MNDRegistrationForm(data)
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_country_and_subdivision_are_validated(self):
        for country, state, invalid_field in (
            ("invalid", "", "country"),
            ("AU", "US-CA", "state"),
            ("AU", "not-a-state", "state"),
        ):
            with self.subTest(country=country, state=state):
                data = self.data()
                data.update(country=country, state=state)
                form = MNDRegistrationForm(data)
                self.assertFalse(form.is_valid())
                self.assertIn(invalid_field, form.errors)
        data = self.data()
        data["state"] = ""
        self.assertTrue(MNDRegistrationForm(data).is_valid())

    def test_guardian_is_optional_and_stale_fields_are_ignored(self):
        data = self.data(guardian=True)
        data.pop("has_guardian")
        data["parent_guardian_date_of_birth"] = "not-a-date"
        response = self.post(data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ParentGuardian.objects.exists())

    def test_guardian_requires_name_phone_and_address_when_selected(self):
        required = (
            "first_name",
            "last_name",
            "phone",
            "country",
            "address",
            "suburb",
            "postcode",
        )
        for name in required:
            field = f"parent_guardian_{name}"
            with self.subTest(field=field):
                data = self.data(guardian=True)
                data.pop(field)
                form = MNDRegistrationForm(data)
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_guardian_dob_gender_and_state_are_optional(self):
        data = self.data(guardian=True)
        data.pop("parent_guardian_state")
        form = MNDRegistrationForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["parent_guardian_date_of_birth"])
        self.assertEqual(form.cleaned_data["parent_guardian_gender"], "")
        self.assertFalse(ParentGuardianForm().fields["gender"].required)

    def test_guardian_optional_fields_are_validated_when_provided(self):
        for field, value in (
            ("parent_guardian_date_of_birth", "not-a-date"),
            (
                "parent_guardian_date_of_birth",
                (timezone.localdate() + timedelta(days=1)).isoformat(),
            ),
            ("parent_guardian_gender", "invalid"),
            ("parent_guardian_state", "US-CA"),
        ):
            with self.subTest(field=field, value=value):
                data = self.data(guardian=True)
                data[field] = value
                form = MNDRegistrationForm(data)
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_registration_saves_patient_contact_and_separate_consent(self):
        before = timezone.now()
        response = self.post()
        self.assertEqual(response.status_code, 302)
        patient = Patient.objects.get()
        user = CustomUser.objects.get()
        self.assertEqual(patient.user, user)
        self.assertEqual(patient.home_phone, self.data()["phone_number"])
        self.assertEqual(patient.email, self.data()["email"])
        self.assertEqual(patient.stage, self.stage)
        self.assertEqual(user.first_name, "Patient")
        self.assertTrue(user.in_group(GROUPS.PATIENT))
        self.assertFalse(user.in_group(GROUPS.PARENT))
        self.assertFalse(user.is_active)
        self.assertEqual(user.preferred_language, "en")
        self.assertEqual(list(user.registry.all()), [self.registry])
        self.assertEqual(patient.working_groups.get().name, "Unallocated")
        address = PatientAddress.objects.get(patient=patient)
        for name in ("address", "suburb", "country", "state", "postcode"):
            self.assertEqual(getattr(address, name), self.data()[name])
        self.assertEqual(address.address_type.type, "Postal")
        consent = RegistrationConsent.objects.get(patient=patient)
        self.assertEqual(consent.accepted_by, user)
        self.assertGreaterEqual(consent.accepted_at, before)
        self.assertEqual(consent.wording, str(RegistrationConsent.WORDING))
        self.assertEqual(consent.language, "en")
        self.assertEqual(
            consent.information_sheet, RegistrationConsent.INFORMATION_SHEET
        )
        self.assertFalse(ConsentValue.objects.exists())
        self.assertFalse(ParentGuardian.objects.exists())
        self.assertEqual(RegistrationProfile.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.data()["email"]])

    def test_guardian_details_do_not_create_or_change_accounts(self):
        response = self.post(self.data(guardian=True))
        self.assertEqual(response.status_code, 302)
        guardian = ParentGuardian.objects.get()
        patient = Patient.objects.get()
        self.assertEqual(guardian.patient.get(), patient)
        self.assertIsNone(guardian.user)
        self.assertIsNone(guardian.self_patient)
        self.assertIsNone(guardian.date_of_birth)
        self.assertEqual(guardian.gender, "")
        self.assertEqual(guardian.phone, "+61 400 654 321")
        self.assertEqual(guardian.address, "456 Other Street")
        self.assertEqual(guardian.postcode, "2000")
        self.assertEqual(guardian.state, "AU-NSW")
        self.assertEqual(CustomUser.objects.count(), 1)
        self.assertEqual(patient.user.first_name, "Patient")

    def test_guardian_dob_and_gender_are_saved_when_supplied(self):
        data = self.data(guardian=True)
        data.update(
            parent_guardian_date_of_birth="1960-05-04",
            parent_guardian_gender="2",
        )
        self.assertEqual(self.post(data).status_code, 302)
        guardian = ParentGuardian.objects.get()
        self.assertEqual(guardian.date_of_birth.isoformat(), "1960-05-04")
        self.assertEqual(guardian.gender, "2")

    def test_unchecked_registration_consent_blocks_all_creation(self):
        data = self.data(guardian=True)
        data.pop("registration_consent")
        response = self.post(data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("registration_consent", response.context["form"].errors)
        self.assertFalse(Patient.objects.exists())
        self.assertFalse(CustomUser.objects.exists())
        self.assertFalse(ParentGuardian.objects.exists())
        self.assertFalse(RegistrationConsent.objects.exists())

    def test_recaptcha_still_blocks_registration(self):
        response = self.post(recaptcha=False)
        self.assertEqual(response.status_code, 200)
        self.assertIn("reCAPTCHA", response.content.decode())
        self.assertFalse(CustomUser.objects.exists())

    def test_password_mismatch_and_duplicate_email_still_fail(self):
        data = self.data()
        data["password2"] = "DifferentPassword!"
        form = MNDRegistrationForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)
        CustomUser.objects.create(username="PATIENT@EXAMPLE.ORG")
        form = MNDRegistrationForm(self.data())
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_registration_failure_rolls_back_user_patient_and_contact(self):
        with (
            patch(
                "mnd.registry.groups.registration.mnd_registration."
                "RegistrationConsent.objects.create",
                side_effect=ValueError("Consent storage failed"),
            ),
            self.assertLogs("rdrf.views.registration_rdrf", level="ERROR"),
        ):
            response = self.post(self.data(guardian=True))
        self.assertRedirects(
            response,
            reverse("registration_failed"),
            fetch_redirect_response=False,
        )
        self.assertFalse(CustomUser.objects.exists())
        self.assertFalse(Patient.objects.exists())
        self.assertFalse(PatientAddress.objects.exists())
        self.assertFalse(ParentGuardian.objects.exists())
        self.assertFalse(RegistrationProfile.objects.exists())
        self.assertFalse(RegistrationConsent.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_registration_page_renders_required_contacts_and_information(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "registration/mnd_registration_form.html"
        )
        self.assertContains(response, "confirmed diagnosis")
        self.assertContains(response, "does not create a guardian account")
        self.assertContains(response, RegistrationConsent.INFORMATION_SHEET)
        self.assertContains(response, "detailed participation consent")
        tree = html.fromstring(response.content)
        self.assertEqual(len(tree.xpath("//form")), 1)
        patient_panel = tree.xpath(
            "//fieldset[legend[normalize-space()='Patient Details']]"
        )
        self.assertEqual(len(patient_panel), 1)
        self.assertNotContains(response, "Patient Contact Details")
        for name in (
            "first_name",
            "surname",
            "date_of_birth",
            "gender",
            *MNDRegistrationForm.contact_field_names,
        ):
            with self.subTest(patient_panel_field=name):
                self.assertTrue(patient_panel[0].xpath(f".//*[@name='{name}']"))
        for name in (
            "phone_number",
            "country",
            "address",
            "suburb",
            "postcode",
            "registration_consent",
        ):
            with self.subTest(name=name):
                element = tree.xpath(f"//*[@name='{name}']")[0]
                self.assertIn("required", element.attrib)
        for name in MNDRegistrationForm.guardian_field_names:
            element = tree.xpath(f"//*[@name='{name}']")[0]
            self.assertNotIn("required", element.attrib)
        self.assertContains(response, 'name="preferred_languages"')
        self.assertContains(response, 'class="g-recaptcha"')

    def test_failed_post_retains_contact_guardian_and_region_values(self):
        data = self.data(guardian=True)
        data["registration_consent"] = ""
        response = self.post(data)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form["address"].value(), data["address"])
        self.assertEqual(form["state"].value(), "AU-QLD")
        self.assertEqual(form["parent_guardian_state"].value(), "AU-NSW")
        self.assertContains(response, 'value="AU-QLD" selected')
        self.assertContains(response, 'value="AU-NSW" selected')
        self.assertTrue(form.fields["parent_guardian_first_name"].required)

    def test_subdivision_endpoint_remains_available_to_registrants(self):
        response = self.client.get(reverse("v1:state_lookup", args=["AU"]))
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            ("AU-QLD", "Queensland"),
            [(region["code"], region["name"]) for region in response.json()],
        )

    def test_consent_admin_is_read_only(self):
        model_admin = admin.site._registry[RegistrationConsent]
        request = RequestFactory().get("/")
        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request))
        self.assertFalse(model_admin.has_delete_permission(request))

    def test_carer_form_is_not_replaced_by_patient_form(self):
        from mnd.views.mnd_registration_view import MNDRegistrationView

        self.assertIs(
            MNDRegistrationView().form_class, MNDCarerRegistrationForm
        )

    @override_settings(MIGRATION_MODULES={})
    def test_registration_consent_migration_matches_model_and_creates_table(
        self,
    ):
        loader = MigrationLoader(connection)
        migration = loader.disk_migrations[("mnd", "0040_registrationconsent")]
        before = loader.project_state(
            [("mnd", "0040_registrationconsent")], at_end=False
        )
        after = migration.mutate_state(before)
        self.assertEqual(
            after.models[("mnd", "registrationconsent")],
            ModelState.from_model(RegistrationConsent),
        )
        for model in ("parentguardian", "historicalparentguardian"):
            self.assertTrue(
                after.models[("patients", model)].fields["gender"].blank
            )
        after.models[("mnd", "registrationconsent")].options["db_table"] = (
            "mnd_registrationconsent_migration_test"
        )
        with connection.schema_editor() as editor:
            migration.operations[0].database_forwards(
                "mnd", editor, before, after
            )
        with connection.cursor() as cursor:
            columns = connection.introspection.get_table_description(
                cursor, "mnd_registrationconsent_migration_test"
            )
        self.assertEqual(
            {column.name for column in columns},
            {
                "id",
                "patient_id",
                "accepted_by_id",
                "accepted_at",
                "wording",
                "information_sheet",
                "language",
            },
        )
