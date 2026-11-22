from __future__ import annotations

import uuid
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("actor_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("actor_role", models.CharField(db_index=True, max_length=32)),
                ("actor_sub_role", models.CharField(blank=True, default="", max_length=32)),
                ("action", models.CharField(db_index=True, max_length=96)),
                ("target_type", models.CharField(db_index=True, max_length=64)),
                ("target_id", models.CharField(db_index=True, max_length=128)),
                ("trace_id", models.CharField(blank=True, db_index=True, default="", max_length=64)),
                ("metadata", models.JSONField(default=dict)),
                ("prev_hash", models.CharField(default="0" * 64, max_length=64)),
                ("record_hash", models.CharField(editable=False, max_length=64, unique=True)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["target_type", "target_id", "-created_at"], name="audit_audit_target__idx"),
                ],
            },
        ),
    ]
