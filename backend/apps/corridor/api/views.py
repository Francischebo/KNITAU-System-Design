from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import AdminSubRole, HasKnitauRole, KnitauRole
from apps.corridor.selectors import rank_mentors_for_passport_skills
from apps.corridor.services import register_diaspora_mentor

from .serializers import CreateDiasporaMentorSerializer, DiasporaMentorMatchSerializer


class MatchedDiasporaMentorListView(APIView):
    permission_classes = [HasKnitauRole]
    required_roles = (KnitauRole.INTERN, KnitauRole.ADMIN)

    @extend_schema(
        summary="Suggest verified diaspora mentors ranked by Career Passport active skill similarity",
        parameters=[
            OpenApiParameter(
                name="skills",
                type=str,
                description="Comma-separated active Career Passport skills.",
                required=False,
            )
        ],
        responses={200: DiasporaMentorMatchSerializer(many=True)},
    )
    def get(self, request):
        raw_skills = request.query_params.get("skills", "")
        active_skills = [s.strip() for s in raw_skills.split(",") if s.strip()]
        ranked = rank_mentors_for_passport_skills(active_skills=active_skills, verified_only=True)
        payload = [
            {
                "id": item.mentor.id,
                "full_name": item.mentor.full_name,
                "country": item.mentor.country,
                "sector": item.mentor.sector,
                "role_title": item.mentor.role_title,
                "bio": item.mentor.bio,
                "expertise_tags": item.mentor.expertise_tags,
                "is_verified": item.mentor.is_verified,
                "similarity_score": item.similarity_score,
                "similarity_label": item.similarity_label,
                "matched_tags": item.matched_tags,
                "matched_skills": item.matched_skills,
            }
            for item in ranked
        ]
        return Response(DiasporaMentorMatchSerializer(payload, many=True).data)


class RegisterDiasporaMentorView(APIView):
    permission_classes = [HasKnitauRole]
    required_roles = (KnitauRole.ADMIN,)
    required_admin_sub_roles = (AdminSubRole.EXECUTIVE, AdminSubRole.CHAPTER_REP)

    @extend_schema(
        summary="Register a new Diaspora Mentor with professional summary and expertise tags",
        request=CreateDiasporaMentorSerializer,
        responses={201: DiasporaMentorMatchSerializer},
    )
    def post(self, request):
        serializer = CreateDiasporaMentorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        mentor = register_diaspora_mentor(
            actor_id=request.user.id,
            actor_role=getattr(request.user, "role", KnitauRole.ADMIN),
            **data,
        )
        return Response(
            {
                "id": mentor.id,
                "full_name": mentor.full_name,
                "country": mentor.country,
                "sector": mentor.sector,
                "role_title": mentor.role_title,
                "bio": mentor.bio,
                "expertise_tags": mentor.expertise_tags,
                "is_verified": mentor.is_verified,
                "similarity_score": 0,
                "similarity_label": "General Mentor",
                "matched_tags": [],
                "matched_skills": [],
            },
            status=status.HTTP_201_CREATED,
        )
