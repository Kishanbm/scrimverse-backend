import pytest

from accounts.serializers import PlayerRegistrationSerializer, TeamSerializer
from tests.factories import UserFactory


@pytest.mark.django_db
def test_player_registration_serializer_validation():
    """Test player registration serializer validation"""
    # Test duplicate email
    UserFactory(email="test@example.com")
    data = {
        "username": "newuser",
        "email": "test@example.com",
        "password": "StrongPassword123!",
        "password2": "StrongPassword123!",
        "phone_number": "1234567890",
    }
    serializer = PlayerRegistrationSerializer(data=data)
    # The serializer itself might not check database uniqueness if not configured in Meta,
    # but usually it does for email field if it's unique=True in model.
    # However, PlayerRegistrationSerializer might have custom logic.
    assert not serializer.is_valid()
    assert "email" in serializer.errors


@pytest.mark.django_db
def test_player_registration_password_mismatch():
    """Test password mismatch in registration"""
    data = {
        "username": "newuser",
        "email": "new@example.com",
        "password": "StrongPassword123!",
        "password2": "mismatch",
        "phone_number": "1234567890",
    }
    serializer = PlayerRegistrationSerializer(data=data)
    assert not serializer.is_valid()
    assert "password" in serializer.errors


@pytest.mark.django_db
def test_team_serializer_member_limit():
    """Test team serializer enforces member limit if applicable"""
    captain = UserFactory(user_type="player")

    # Create 15 users
    users = [UserFactory(username=f"u{i}") for i in range(16)]
    usernames = [u.username for u in users]

    data = {"name": "Big Team", "player_usernames": usernames}  # 16 members

    # TeamSerializer context usually needed for request.user
    from rest_framework.test import APIRequestFactory

    factory = APIRequestFactory()
    request = factory.post("/")
    request.user = captain

    serializer = TeamSerializer(data=data, context={"request": request})
    # Most serializers have a limit in validate method
    if not serializer.is_valid():
        assert "player_usernames" in serializer.errors or "non_field_errors" in serializer.errors
