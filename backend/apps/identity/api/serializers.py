from __future__ import annotations

from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=10, write_only=True)
    full_name = serializers.CharField(max_length=160)
    role = serializers.ChoiceField(choices=["intern", "employer", "institution"])
    phone_e164 = serializers.CharField(max_length=20, required=False, default="")
    national_id = serializers.CharField(max_length=32, required=False, default="", write_only=True)
    institution_name = serializers.CharField(max_length=160, required=False, default="")
    employer_name = serializers.CharField(max_length=160, required=False, default="")


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserProfileSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    full_name = serializers.CharField()
    role = serializers.CharField()
    admin_sub_role = serializers.CharField(allow_blank=True)
    kyc_verified = serializers.BooleanField()


class AuthTokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    user = UserProfileSerializer()
