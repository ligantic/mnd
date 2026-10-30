import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mnd", "0039_add_mims_cache"),
        ("patients", "0069_alter_historicalparentguardian_gender_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="RegistrationConsent",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("accepted_at", models.DateTimeField(auto_now_add=True)),
                ("wording", models.TextField()),
                ("information_sheet", models.CharField(max_length=255)),
                ("language", models.CharField(max_length=20)),
                (
                    "accepted_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "patient",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="registration_consent",
                        to="patients.patient",
                    ),
                ),
            ],
        ),
    ]
