from __future__ import annotations

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.services import record_audit_event
from apps.identity.services import authenticate_account, register_account

from .serializers import (
    AuthTokenResponseSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserProfileSerializer,
)

REFRESH_COOKIE_NAME = "knitau_refresh"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=max_age,
        httponly=True,
        secure=True,
        samesite="None",
        path="/api/v1/auth/",
    )


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Register a new intern, employer, or institution account",
        request=RegisterSerializer,
        responses={201: UserProfileSerializer},
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = register_account(**serializer.validated_data)
        return Response(UserProfileSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Authenticate user and issue short-lived access JWT + HttpOnly refresh cookie",
        request=LoginSerializer,
        responses={200: AuthTokenResponseSerializer},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate_account(
            request=request,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        refresh = RefreshToken.for_user(user)
        response = Response(
            {
                "access": str(refresh.access_token),
                "user": UserProfileSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )
        _set_refresh_cookie(response, str(refresh))
        return response


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="Rotate HttpOnly refresh cookie into a fresh access JWT")
    def post(self, request):
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if not raw_refresh:
            return Response(
                {"error": {"code": "missing_refresh_token", "message": "Session expired."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            refresh = RefreshToken(raw_refresh)
            access = str(refresh.access_token)
            if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
                refresh.set_jti()
                refresh.set_exp()
            response = Response({"access": access}, status=status.HTTP_200_OK)
            _set_refresh_cookie(response, str(refresh))
            return response
        except TokenError:
            return Response(
                {"error": {"code": "invalid_refresh_token", "message": "Invalid or expired session."}},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Revoke refresh token cookie and record logout audit event")
    def post(self, request):
        raw_refresh = request.COOKIES.get(REFRESH_COOKIE_NAME)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass
        record_audit_event(
            actor_id=request.user.id,
            actor_role=request.user.role,
            actor_sub_role=request.user.admin_sub_role,
            action="identity.auth.logout",
            target_type="User",
            target_id=str(request.user.id),
        )
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth/")
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(summary="Return current authenticated user profile and role scope", responses={200: UserProfileSerializer})
    def get(self, request):
        return Response(UserProfileSerializer(request.user).data)
