from __future__ import annotations

from django.db import migrations


def apply_immutable_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_auditlog_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_auditlog is append-only and immutable';
        END;
        $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_auditlog_immutable ON audit_auditlog;
        CREATE TRIGGER trg_auditlog_immutable
        BEFORE UPDATE OR DELETE ON audit_auditlog
        FOR EACH ROW EXECUTE FUNCTION prevent_auditlog_mutation();
        """
    )


def revert_immutable_triggers(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        """
        DROP TRIGGER IF EXISTS trg_auditlog_immutable ON audit_auditlog;
        DROP FUNCTION IF EXISTS prevent_auditlog_mutation();
        """
    )


class Migration(migrations.Migration):
    dependencies = [
        ("audit", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(apply_immutable_triggers, reverse_code=revert_immutable_triggers),
    ]
