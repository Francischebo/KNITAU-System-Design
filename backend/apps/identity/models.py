from __future__ import annotations

import hashlib
import hmac
import uuid
from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.common.permissions import AdminSubRole, KnitauRole


class KnitauUserManager(BaseUserManager):
    def create_user(
        self,
        email: str,
        password: str | None = None,
        *,
        role: str = KnitauRole.INTERN,
        full_name: str = "",
        **extra_fields,
    ):
        if not email:
            raise ValueError("Email address is required.")
        normalized_email = self.normalize_email(email).lower()
        user = self.model(
            email=normalized_email,
            role=role,
            full_name=full_name.strip(),
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", KnitauRole.ADMIN)
        extra_fields.setdefault("admin_sub_role", AdminSubRole.EXECUTIVE)
        return self.create_user(email=email, password=password, **extra_fields)


def hash_national_id(raw_national_id: str) -> str:
    """Deterministic salted HMAC-SHA256 digest for Kenya DPA 2019 PII protection."""
    cleaned = raw_national_id.strip().upper()
    return hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        cleaned.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [(r.value, r.name.title()) for r in KnitauRole]
    SUB_ROLE_CHOICES = [(sr.value, sr.name.replace("_", " ").title()) for sr in AdminSubRole]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    phone_e164 = models.CharField(max_length=20, blank=True, default="", db_index=True)
    full_name = models.CharField(max_length=160)
    role = models.CharField(max_length=24, choices=ROLE_CHOICES, default=KnitauRole.INTERN, db_index=True)
    admin_sub_role = models.CharField(
        max_length=32, choices=SUB_ROLE_CHOICES, blank=True, default=""
    )
    institution_name = models.CharField(max_length=160, blank=True, default="")
    employer_name = models.CharField(max_length=160, blank=True, default="")
    national_id_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)
    kyc_verified = models.BooleanField(default=False)
    consent_accepted_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    objects = KnitauUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.email} ({self.role})"
