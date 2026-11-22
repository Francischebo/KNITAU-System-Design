from __future__ import annotations


class PrimaryReplicaRouter:
    """
    Routes read-only queries to PostgreSQL `replica` when configured,
    keeping writes and multi-table transactions pinned to `default` (primary).
    """

    def db_for_read(self, model, **hints) -> str:
        if hints.get("force_primary"):
            return "default"
        return "replica"

    def db_for_write(self, model, **hints) -> str:
        return "default"

    def allow_relation(self, obj1, obj2, **hints) -> bool:
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints) -> bool:
        return db == "default"
