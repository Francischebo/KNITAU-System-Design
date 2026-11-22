from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.common.permissions import KnitauRole


@pytest.mark.django_db
def test_self_registration_blocks_admin_privilege_escalation():
    client = APIClient()
    resp = client.post(
        "/api/v1/auth/register/",
        {
            "email": "attacker@example.com",
            "password": "StrongPassword!123",
            "full_name": "Test User",
            "role": KnitauRole.ADMIN,
        },
        format="json",
    )
    assert resp.status_code in {400, 403}


@pytest.mark.django_db
def test_intern_register_login_and_me_profile():
    client = APIClient()
    reg = client.post(
        "/api/v1/auth/register/",
        {
            "email": "amina.otieno@example.com",
            "password": "StrongPassword!123",
            "full_name": "Amina Otieno",
            "role": KnitauRole.INTERN,
            "national_id": "34567890",
        },
        format="json",
    )
    assert reg.status_code == 201

    login = client.post(
        "/api/v1/auth/login/",
        {"email": "amina.otieno@example.com", "password": "StrongPassword!123"},
        format="json",
    )
    assert login.status_code == 200
    access = login.data["access"]
    assert "knitau_refresh" in login.cookies

    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    me = client.get("/api/v1/auth/me/")
    assert me.status_code == 200
    assert me.data["role"] == KnitauRole.INTERN
    assert AuditLog.objects.filter(action="identity.auth.login_succeeded").exists()
