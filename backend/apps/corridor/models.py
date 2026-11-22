from __future__ import annotations

from django.db import models

from apps.common.models import SoftDeleteModel, UUIDTimeStampedModel


class DiasporaMentor(SoftDeleteModel):
    full_name = models.CharField(max_length=160)
    country = models.CharField(max_length=80, db_index=True)
    sector = models.CharField(max_length=120, db_index=True)
    role_title = models.CharField(max_length=160)
    bio = models.TextField(
        help_text="Brief professional summary highlighting career journey and mentorship focus."
    )
    expertise_tags = models.JSONField(default=list)
    is_verified = models.BooleanField(default=False, db_index=True)
    capacity = models.PositiveSmallIntegerField(default=3)
    active_mentees_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-is_verified", "full_name"]


class MentorMatchRequest(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    mentor = models.ForeignKey(
        DiasporaMentor, on_delete=models.PROTECT, related_name="match_requests"
    )
    intern_user_id = models.UUIDField(db_index=True)
    similarity_score = models.PositiveSmallIntegerField(default=0)
    matched_tags = models.JSONField(default=list)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["mentor", "intern_user_id"],
                condition=models.Q(status__in=["pending", "accepted"]),
                name="unique_active_mentor_request_per_intern",
            )
        ]
