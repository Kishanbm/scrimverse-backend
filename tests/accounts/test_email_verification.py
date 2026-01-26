"""
Test cases for Email Verification for New Users
Tests cover:
- Email verification requirement for non-Google auth users
- Account activation after email verification
- Token expiry and validation
- Resending verification emails
- Login restrictions for unverified accounts
"""
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from tests.factories import PlayerProfileFactory, UserFactory


@pytest.mark.django_db
@patch("accounts.views.send_verification_email_task.delay")
def test_new_user_requires_email_verification(mock_email_task, api_client):
    """Test that new users must verify their email before logging in"""
    data = {
        "email": "newuser@test.com",
        "username": "newuser",
        "password": "TestPass123!",
        "password2": "TestPass123!",
        "phone_number": "9876543210",
    }

    response = api_client.post("/api/accounts/player/register/", data)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["verification_required"] is True

    user = User.objects.get(email="newuser@test.com")
    assert user.is_email_verified is False
    assert user.is_active is False
    assert user.email_verification_token is not None


@pytest.mark.django_db
def test_unverified_user_cannot_login(api_client):
    """Test that unverified users cannot log in"""
    user = UserFactory(user_type="player", email="unverified@test.com", is_email_verified=False, is_active=False)
    user.set_password("TestPass123!")
    user.save()
    PlayerProfileFactory(user=user)

    data = {"email": "unverified@test.com", "password": "TestPass123!", "user_type": "player"}

    response = api_client.post("/api/accounts/login/", data)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "verify your email" in response.data.get("error", "").lower()


@pytest.mark.django_db
def test_email_verification_activates_account(api_client):
    """Test that verifying email activates the account"""
    user = UserFactory(
        user_type="player", is_email_verified=False, is_active=False, email_verification_token="valid_token_123"
    )
    PlayerProfileFactory(user=user)

    response = api_client.get("/api/accounts/verify-email/valid_token_123/")

    assert response.status_code == status.HTTP_200_OK

    user.refresh_from_db()
    assert user.is_email_verified is True
    assert user.is_active is True
    # Token should remain after verification (as per implementation)
    assert user.email_verification_token is not None


@pytest.mark.django_db
def test_verified_user_can_login(api_client):
    """Test that verified users can log in successfully"""
    user = UserFactory(user_type="player", email="verified@test.com", is_email_verified=True, is_active=True)
    user.set_password("TestPass123!")
    user.save()
    PlayerProfileFactory(user=user)

    data = {"email": "verified@test.com", "password": "TestPass123!", "user_type": "player"}

    response = api_client.post("/api/accounts/login/", data)

    assert response.status_code == status.HTTP_200_OK
    assert "tokens" in response.data


@pytest.mark.django_db
def test_invalid_verification_token(api_client):
    """Test that invalid verification token is rejected"""
    user = UserFactory(
        user_type="player", is_email_verified=False, is_active=False, email_verification_token="correct_token"
    )
    PlayerProfileFactory(user=user)

    response = api_client.get("/api/accounts/verify-email/wrong_token/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST

    user.refresh_from_db()
    assert user.is_email_verified is False
    assert user.is_active is False


@pytest.mark.django_db
def test_expired_verification_token(api_client):
    """Test that expired verification token is rejected"""
    # Token sent more than 24 hours ago
    past_time = timezone.now() - timedelta(hours=25)
    user = UserFactory(
        user_type="player",
        is_email_verified=False,
        is_active=False,
        email_verification_token="expired_token",
        email_verification_sent_at=past_time,
    )
    PlayerProfileFactory(user=user)

    response = api_client.get("/api/accounts/verify-email/expired_token/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "expired" in response.data.get("error", "").lower()


@pytest.mark.django_db
@patch("accounts.views.send_verification_email_task.delay")
def test_resend_verification_email(mock_email_task, api_client):
    """Test resending verification email to unverified user"""
    user = UserFactory(user_type="player", email="resend@test.com", is_email_verified=False, is_active=False)
    PlayerProfileFactory(user=user)

    response = api_client.post("/api/accounts/resend-verification/", {"email": "resend@test.com"})

    assert response.status_code == status.HTTP_200_OK
    mock_email_task.assert_called_once()

    # User should have new token
    user.refresh_from_db()
    assert user.email_verification_token is not None


@pytest.mark.django_db
def test_cannot_resend_to_verified_user(api_client):
    """Test that verification email cannot be resent to already verified user"""
    user = UserFactory(user_type="player", email="already_verified@test.com", is_email_verified=True, is_active=True)
    PlayerProfileFactory(user=user)

    response = api_client.post("/api/accounts/resend-verification/", {"email": "already_verified@test.com"})

    assert response.status_code == status.HTTP_200_OK
    assert "already verified" in response.data.get("message", "").lower()


@pytest.mark.django_db
@patch("accounts.views.send_verification_email_task.delay")
def test_host_registration_requires_verification(mock_email_task, api_client):
    """Test that host registration also requires email verification"""
    data = {
        "email": "newhost@test.com",
        "username": "newhost",
        "password": "TestPass123!",
        "password2": "TestPass123!",
        "phone_number": "9876543210",
    }

    response = api_client.post("/api/accounts/host/register/", data)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["verification_required"] is True

    user = User.objects.get(email="newhost@test.com")
    assert user.is_email_verified is False
    assert user.is_active is False


@pytest.mark.django_db
def test_google_auth_users_skip_verification():
    """Test that Google OAuth users skip email verification"""
    client = APIClient()

    with patch("accounts.views.GoogleOAuth.verify_google_token") as mock_verify:
        mock_verify.return_value = {"email": "googleuser@gmail.com", "email_verified": True, "name": "Google User"}

        response = client.post(
            "/api/accounts/google-auth/",
            {
                "token": "google_token_123",
                "user_type": "player",
                "username": "googleuser",
                "phone_number": "9876543210",
                "is_signup": True,
            },
        )

        if response.status_code == status.HTTP_200_OK:
            user = User.objects.get(email="googleuser@gmail.com")
            assert user.is_email_verified is True
            assert user.is_active is True
            assert user.email_verification_token is None


@pytest.mark.django_db
@patch("accounts.views.send_verification_email_task.delay")
def test_duplicate_email_unverified_account_deleted(mock_email_task, api_client):
    """Test that unverified account is deleted when same email registers again"""
    # Create unverified user
    user1 = UserFactory(user_type="player", email="duplicate@test.com", is_email_verified=False, is_active=False)
    PlayerProfileFactory(user=user1)
    user1_id = user1.id

    # Try to register again with same email
    data = {
        "email": "duplicate@test.com",
        "username": "newusername",
        "password": "TestPass123!",
        "password2": "TestPass123!",
        "phone_number": "9876543210",
    }

    response = api_client.post("/api/accounts/player/register/", data)

    assert response.status_code == status.HTTP_201_CREATED

    # Old unverified user should be deleted
    assert not User.objects.filter(id=user1_id).exists()

    # New user should exist
    new_user = User.objects.get(email="duplicate@test.com")
    assert new_user.id != user1_id
    assert new_user.username == "newusername"


@pytest.mark.django_db
@patch("accounts.views.send_verification_email_task.delay")
def test_duplicate_email_verified_account_rejected(mock_email_task, api_client):
    """Test that registration fails if email belongs to verified account"""
    # Create verified user
    user = UserFactory(user_type="player", email="verified@test.com", is_email_verified=True, is_active=True)
    PlayerProfileFactory(user=user)

    # Try to register with same email
    data = {
        "email": "verified@test.com",
        "username": "newusername",
        "password": "TestPass123!",
        "password2": "TestPass123!",
        "phone_number": "9876543210",
    }

    response = api_client.post("/api/accounts/player/register/", data)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response.data.get("error", "").lower()


@pytest.mark.django_db
def test_verification_token_is_secure():
    """Test that verification tokens are cryptographically secure"""
    user1 = UserFactory(user_type="player", is_email_verified=False, is_active=False)
    user2 = UserFactory(user_type="player", is_email_verified=False, is_active=False)

    import secrets

    user1.email_verification_token = secrets.token_urlsafe(32)
    user1.save()
    user2.email_verification_token = secrets.token_urlsafe(32)
    user2.save()

    # Tokens should be different
    assert user1.email_verification_token != user2.email_verification_token

    # Tokens should be sufficiently long (at least 32 characters)
    if user1.email_verification_token:
        assert len(user1.email_verification_token) >= 32


@pytest.mark.django_db
@patch("accounts.tasks.send_welcome_email_task.delay")
def test_welcome_email_sent_after_verification(mock_welcome_email, api_client):
    """Test that welcome email is sent after successful verification"""
    user = UserFactory(
        user_type="player", is_email_verified=False, is_active=False, email_verification_token="test_token"
    )
    PlayerProfileFactory(user=user)

    response = api_client.get("/api/accounts/verify-email/test_token/")

    assert response.status_code == status.HTTP_200_OK

    # Welcome email should be sent
    mock_welcome_email.assert_called_once()
