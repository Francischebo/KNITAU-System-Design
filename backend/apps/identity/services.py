from __future__ import annotations

from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from rest_framework import status

from apps.audit.services import record_audit_event
from apps.common.exceptions import DomainError
from apps.common.permissions import KnitauRole

from .models import User, hash_national_id

_SELF_REGISTRATION_ROLES = frozenset(
    {KnitauRole.INTERN.value, KnitauRole.EMPLOYER.value, KnitauRole.INSTITUTION.value}
)


@transaction.atomic
def register_account(
    *,
    email: str,
    password: str,
    full_name: str,
    role: str,
    phone_e164: str = "",
    national_id: str = "",
    institution_name: str = "",
    employer_name: str = "",
) -> User:
    if role not in _SELF_REGISTRATION_ROLES:
        raise DomainError(
            code="forbidden_role_registration",
            message="Self-registration is restricted to intern, employer, and institution accounts.",
            http_status=status.HTTP_403_FORBIDDEN,
        )

    normalized_email = email.strip().lower()
    if User.objects.filter(email=normalized_email).exists():
        raise DomainError(
            code="email_already_registered",
            message="An account with this email already exists.",
            http_status=status.HTTP_409_CONFLICT,
        )

    user = User.objects.create_user(
        email=normalized_email,
        password=password,
        role=role,
        full_name=full_name,
        phone_e164=phone_e164.strip(),
        institution_name=institution_name.strip(),
        employer_name=employer_name.strip(),
        national_id_hash=hash_national_id(national_id) if national_id.strip() else "",
        consent_accepted_at=timezone.now(),
    )

    record_audit_event(
        actor_id=user.id,
        actor_role=user.role,
        action="identity.user.registered",
        target_type="User",
        target_id=str(user.id),
        metadata={"role": user.role},
    )
    return user


def authenticate_account(*, request, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    user = authenticate(request=request, username=normalized_email, password=password)
    if user is None or not user.is_active:
        record_audit_event(
            actor_id=None,
            actor_role="anonymous",
            action="identity.auth.login_failed",
            target_type="User",
            target_id=normalized_email,
        )
        raise DomainError(
            code="invalid_credentials",
            message="Invalid email or password.",
            http_status=status.HTTP_401_UNAUTHORIZED,
        )

    record_audit_event(
        actor_id=user.id,
        actor_role=user.role,
        actor_sub_role=user.admin_sub_role,
        action="identity.auth.login_succeeded",
        target_type="User",
        target_id=str(user.id),
    )
    return user
