from __future__ import annotations

import uuid
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(db_index=True, max_length=254, unique=True)),
                ("phone_e164", models.CharField(blank=True, db_index=True, default="", max_length=20)),
                ("full_name", models.CharField(max_length=160)),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("intern", "Intern"),
                            ("employer", "Employer"),
                            ("institution", "Institution"),
                            ("admin", "Admin"),
                        ],
                        db_index=True,
                        default="intern",
                        max_length=24,
                    ),
                ),
                (
                    "admin_sub_role",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("executive", "Executive"),
                            ("case_officer", "Case Officer"),
                            ("finance_officer", "Finance Officer"),
                            ("chapter_rep", "Chapter Rep"),
                        ],
                        default="",
                        max_length=32,
                    ),
                ),
                ("institution_name", models.CharField(blank=True, default="", max_length=160)),
                ("employer_name", models.CharField(blank=True, default="", max_length=160)),
                ("national_id_hash", models.CharField(blank=True, db_index=True, default="", max_length=64)),
                ("kyc_verified", models.BooleanField(default=False)),
                ("consent_accepted_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("is_staff", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True, related_name="user_set", related_query_name="user", to="auth.group"
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True, related_name="user_set", related_query_name="user", to="auth.permission"
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
