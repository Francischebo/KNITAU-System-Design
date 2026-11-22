from __future__ import annotations

from enum import StrEnum
from rest_framework.permissions import BasePermission


class KnitauRole(StrEnum):
    INTERN = "intern"
    EMPLOYER = "employer"
    INSTITUTION = "institution"
    ADMIN = "admin"


class AdminSubRole(StrEnum):
    EXECUTIVE = "executive"
    CASE_OFFICER = "case_officer"
    FINANCE_OFFICER = "finance_officer"
    CHAPTER_REP = "chapter_rep"


class HasKnitauRole(BasePermission):
    """
    Central RBAC permission class. Views declare `required_roles` and optional
    `required_admin_sub_roles` to enforce Single Source of Truth access control.
    """

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        required_roles = getattr(view, "required_roles", None)
        if not required_roles:
            return True

        user_role = getattr(user, "role", None)
        if user_role not in required_roles:
            return False

        if user_role == KnitauRole.ADMIN:
            required_sub_roles = getattr(view, "required_admin_sub_roles", None)
            if required_sub_roles:
                user_sub_role = getattr(user, "admin_sub_role", None)
                return user_sub_role in required_sub_roles

        return True
