from __future__ import annotations

from django.db import transaction

from apps.audit.services import record_audit_event
from apps.common.events import DomainEvent, publish_event
from apps.common.exceptions import DomainError

from .models import DiasporaMentor, MentorMatchRequest
from .selectors import calculate_tag_skill_similarity


@transaction.atomic
def register_diaspora_mentor(
    *,
    actor_id,
    actor_role: str,
    full_name: str,
    country: str,
    sector: str,
    role_title: str,
    bio: str,
    expertise_tags: list[str],
    capacity: int = 3,
    auto_verify: bool = False,
) -> DiasporaMentor:
    cleaned_tags = [tag.strip() for tag in expertise_tags if tag and tag.strip()]
    if not cleaned_tags:
        raise DomainError(
            code="missing_expertise_tags",
            message="At least one expertise tag is required to enable Passport skill matching.",
        )

    mentor = DiasporaMentor.objects.create(
        full_name=full_name.strip(),
        country=country.strip(),
        sector=sector.strip(),
        role_title=role_title.strip(),
        bio=bio.strip(),
        expertise_tags=cleaned_tags,
        capacity=capacity,
        is_verified=auto_verify,
    )

    record_audit_event(
        actor_id=actor_id,
        actor_role=actor_role,
        action="corridor.mentor.registered",
        target_type="DiasporaMentor",
        target_id=str(mentor.id),
        metadata={"country": mentor.country, "sector": mentor.sector, "verified": mentor.is_verified},
    )
    return mentor


@transaction.atomic
def request_mentorship(
    *,
    intern_user_id,
    mentor_id,
    active_passport_skills: list[str],
) -> MentorMatchRequest:
    mentor = DiasporaMentor.objects.select_for_update().active().filter(id=mentor_id).first()
    if not mentor or not mentor.is_verified:
        raise DomainError(
            code="mentor_unavailable",
            message="Selected diaspora mentor is unavailable or not yet verified.",
            http_status=404,
        )

    if mentor.active_mentees_count >= mentor.capacity:
        raise DomainError(
            code="mentor_at_capacity",
            message="This diaspora mentor has reached active mentorship capacity.",
            http_status=409,
        )

    already_open = MentorMatchRequest.objects.filter(
        mentor=mentor,
        intern_user_id=intern_user_id,
        status__in=[MentorMatchRequest.Status.PENDING, MentorMatchRequest.Status.ACCEPTED],
    ).exists()
    if already_open:
        raise DomainError(
            code="duplicate_mentorship_request",
            message="You already have an active or pending request with this mentor.",
            http_status=409,
        )

    score, _, matched_tags, _ = calculate_tag_skill_similarity(
        mentor.expertise_tags, active_passport_skills, mentor.is_verified
    )

    match_request = MentorMatchRequest.objects.create(
        mentor=mentor,
        intern_user_id=intern_user_id,
        similarity_score=score,
        matched_tags=matched_tags,
    )

    record_audit_event(
        actor_id=intern_user_id,
        actor_role="intern",
        action="corridor.mentorship.requested",
        target_type="MentorMatchRequest",
        target_id=str(match_request.id),
        metadata={"mentor_id": str(mentor.id), "similarity_score": score},
    )

    publish_event(
        DomainEvent(
            event_name="corridor.mentorship.requested",
            payload={"match_request_id": str(match_request.id), "mentor_id": str(mentor.id)},
        )
    )
    return match_request
