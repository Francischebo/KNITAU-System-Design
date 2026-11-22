from __future__ import annotations

import uuid
import pytest

from apps.audit.models import AuditLog
from apps.corridor.selectors import calculate_tag_skill_similarity, rank_mentors_for_passport_skills
from apps.corridor.services import register_diaspora_mentor


def test_similarity_prioritizes_direct_and_synonym_skill_overlap():
    score_strong, label_strong, matched_tags, matched_skills = calculate_tag_skill_similarity(
        expertise_tags=["Solar PV Systems", "Grid Engineering"],
        active_skills=["Renewable Energy"],
        is_verified=True,
    )
    score_weak, label_weak, _, _ = calculate_tag_skill_similarity(
        expertise_tags=["Tax Advisory", "Audit Compliance"],
        active_skills=["Renewable Energy"],
        is_verified=True,
    )

    assert score_strong > score_weak
    assert label_strong in {"Strong Match", "Partial Match"}
    assert label_weak == "General Mentor"
    assert "Solar PV Systems" in matched_tags
    assert "Renewable Energy" in matched_skills


@pytest.mark.django_db
def test_register_mentor_and_rank_writes_immutable_audit_event():
    actor_id = uuid.uuid4()
    mentor = register_diaspora_mentor(
        actor_id=actor_id,
        actor_role="admin",
        full_name="Dr. Wanjiku Njoroge",
        country="Germany",
        sector="Clean Energy",
        role_title="Lead Grid Architect",
        bio="12 years designing utility-scale solar and microgrid corridors across East Africa and Europe.",
        expertise_tags=["Solar Microgrids", "Energy Policy", "CAD"],
        auto_verify=True,
    )

    ranked = rank_mentors_for_passport_skills(active_skills=["Solar Microgrids", "Python"])
    assert ranked[0].mentor.id == mentor.id
    assert ranked[0].similarity_score >= 65
    assert AuditLog.objects.filter(
        action="corridor.mentor.registered", target_id=str(mentor.id)
    ).exists()
