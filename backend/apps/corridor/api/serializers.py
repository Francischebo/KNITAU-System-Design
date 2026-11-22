from __future__ import annotations

from rest_framework import serializers


class DiasporaMentorMatchSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    country = serializers.CharField()
    sector = serializers.CharField()
    role_title = serializers.CharField()
    bio = serializers.CharField()
    expertise_tags = serializers.ListField(child=serializers.CharField())
    is_verified = serializers.BooleanField()
    similarity_score = serializers.IntegerField(min_value=0, max_value=99)
    similarity_label = serializers.CharField()
    matched_tags = serializers.ListField(child=serializers.CharField())
    matched_skills = serializers.ListField(child=serializers.CharField())


class CreateDiasporaMentorSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=160)
    country = serializers.CharField(max_length=80)
    sector = serializers.CharField(max_length=120)
    role_title = serializers.CharField(max_length=160)
    bio = serializers.CharField(min_length=10, max_length=800)
    expertise_tags = serializers.ListField(child=serializers.CharField(max_length=64), min_length=1)
    capacity = serializers.IntegerField(min_value=1, max_value=20, default=3)
    auto_verify = serializers.BooleanField(default=False)
