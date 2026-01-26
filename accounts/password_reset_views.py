"""
Password Reset Views
Handles password reset for users (players and hosts)
"""

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from accounts.tasks import send_password_reset_email_task

logger = logging.getLogger(__name__)


class RequestPasswordResetView(APIView):
    """
    Request password reset email
    POST /api/accounts/request-password-reset/
    Body: {"email": "user@example.com", "user_type": "player"}
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        user_type = request.data.get("user_type", "").strip().lower()

        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

        if not user_type or user_type not in ["player", "host"]:
            return Response(
                {"error": "Valid user_type is required (player or host)"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Find user with matching email AND user_type
            user = User.objects.get(email=email, user_type=user_type)

            # Check if password reset email was sent recently (prevent spam)
            if user.password_reset_sent_at:
                time_since_last_email = timezone.now() - user.password_reset_sent_at
                if time_since_last_email < timedelta(minutes=2):
                    seconds_remaining = 120 - int(time_since_last_email.total_seconds())
                    return Response(
                        {"error": f"Please wait {seconds_remaining} seconds before requesting another reset email"},
                        status=status.HTTP_429_TOO_MANY_REQUESTS,
                    )

            # Generate new password reset token
            reset_token = secrets.token_urlsafe(32)
            user.password_reset_token = reset_token
            user.password_reset_sent_at = timezone.now()
            user.save(update_fields=["password_reset_token", "password_reset_sent_at"])

            # Build reset URL
            frontend_url = settings.CORS_ALLOWED_ORIGINS[0]
            reset_url = f"{frontend_url}/reset-password/{reset_token}"

            # Send password reset email asynchronously
            send_password_reset_email_task.delay(
                user_email=user.email, user_name=user.username, reset_url=reset_url, user_type=user.user_type
            )

            logger.info(f"Password reset email sent to: {user.email} (type: {user.user_type})")

            return Response(
                {"message": "Password reset email sent successfully. Please check your inbox.", "email": user.email},
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            # For security, don't reveal if email exists or user_type mismatch
            # Return success message anyway to prevent email enumeration
            logger.warning(
                f"Password reset requested for email: {email} with user_type: {user_type} - Not found or mismatch"
            )
            return Response(
                {
                    "message": "If an account with that email and type exists, a password reset link has been sent.",
                    "email": email,
                },
                status=status.HTTP_200_OK,
            )


class ResetPasswordView(APIView):
    """
    Reset password with token
    POST /api/accounts/reset-password/<token>/
    Body: {"new_password": "newpassword123"}
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, token):
        logger.info(f"🔍 Password reset attempt with token: {token[:10]}...")

        new_password = request.data.get("new_password", "").strip()

        if not new_password:
            return Response({"error": "New password is required"}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response(
                {"error": "Password must be at least 8 characters long"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Find user with this token
            user = User.objects.get(password_reset_token=token)
            logger.info(f"✅ Found user: {user.email} (type: {user.user_type})")

            # Check if token has expired (24 hours)
            if user.password_reset_sent_at:
                time_since_sent = timezone.now() - user.password_reset_sent_at
                if time_since_sent > timedelta(hours=24):
                    logger.warning(f"⚠️ Password reset token expired for user: {user.email}")
                    return Response(
                        {
                            "error": "Password reset link has expired. Please request a new one.",
                            "expired": True,
                            "user_type": user.user_type,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Reset password
            user.password = make_password(new_password)
            user.password_reset_token = None  # Clear the token
            user.password_reset_sent_at = None
            user.save(update_fields=["password", "password_reset_token", "password_reset_sent_at"])

            logger.info(f"✅ Password reset successful for user: {user.email}")

            # Generate JWT tokens for auto-login
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)

            # Return success with tokens for auto-login
            return Response(
                {
                    "message": "Password reset successful! Logging you in...",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "user_type": user.user_type,
                        "is_email_verified": user.is_email_verified,
                    },
                    "tokens": {"access": access_token, "refresh": refresh_token},
                    "user_type": user.user_type,
                },
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            logger.error(f"❌ Invalid password reset token: {token[:10]}...")
            return Response(
                {"error": "Invalid or expired password reset link", "invalid": True}, status=status.HTTP_400_BAD_REQUEST
            )


class VerifyResetTokenView(APIView):
    """
    Verify if password reset token is valid
    GET /api/accounts/verify-reset-token/<token>/
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        logger.info(f"🔍 Verifying password reset token: {token[:10]}...")

        try:
            user = User.objects.get(password_reset_token=token)

            # Check if token has expired (24 hours)
            if user.password_reset_sent_at:
                time_since_sent = timezone.now() - user.password_reset_sent_at
                if time_since_sent > timedelta(hours=24):
                    logger.warning(f"⚠️ Password reset token expired for user: {user.email}")
                    return Response(
                        {
                            "valid": False,
                            "error": "Password reset link has expired. Please request a new one.",
                            "expired": True,
                            "user_type": user.user_type,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            logger.info(f"✅ Valid token for user: {user.email}")
            return Response(
                {
                    "valid": True,
                    "email": user.email,
                    "username": user.username,
                    "user_type": user.user_type,
                },
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            logger.error(f"❌ Invalid password reset token: {token[:10]}...")
            return Response(
                {"valid": False, "error": "Invalid or expired password reset link", "invalid": True},
                status=status.HTTP_400_BAD_REQUEST,
            )
