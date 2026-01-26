"""
Comprehensive tests for Account Views
Tests cover profile management, user search, and account operations
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import TeamMember
from tests.factories import HostProfileFactory, PlayerProfileFactory, UserFactory


@pytest.mark.django_db
def test_get_current_user_profile_player():
    """Test player can get their own profile"""
    player_profile = PlayerProfileFactory()

    client = APIClient()
    client.force_authenticate(user=player_profile.user)

    response = client.get("/api/accounts/me/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["user"]["email"] == player_profile.user.email
    assert "profile" in response.data


@pytest.mark.django_db
def test_get_current_user_profile_host():
    """Test host can get their own profile"""
    host_profile = HostProfileFactory()

    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    response = client.get("/api/accounts/me/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["user"]["email"] == host_profile.user.email
    assert "profile" in response.data


@pytest.mark.django_db
def test_update_current_user_username():
    """Test user can update their username"""
    player_profile = PlayerProfileFactory()

    client = APIClient()
    client.force_authenticate(user=player_profile.user)

    data = {"username": "newusername"}

    response = client.patch("/api/accounts/me/", data, format="json")

    assert response.status_code == status.HTTP_200_OK
    player_profile.user.refresh_from_db()
    assert player_profile.user.username == "newusername"


@pytest.mark.django_db
def test_cannot_update_email():
    """Test user cannot change their email"""
    player_profile = PlayerProfileFactory()
    original_email = player_profile.user.email

    client = APIClient()
    client.force_authenticate(user=player_profile.user)

    data = {"email": "newemail@test.com"}

    client.patch("/api/accounts/me/", data, format="json")

    # Email should not change
    player_profile.user.refresh_from_db()
    assert player_profile.user.email == original_email


@pytest.mark.django_db
def test_update_player_profile():
    """Test player can update their profile"""
    player_profile = PlayerProfileFactory()

    client = APIClient()
    client.force_authenticate(user=player_profile.user)

    data = {"bio": "Updated bio", "favorite_game": "BGMI"}

    response = client.patch("/api/accounts/player/profile/me/", data, format="json")

    assert response.status_code == status.HTTP_200_OK
    player_profile.refresh_from_db()
    assert player_profile.bio == "Updated bio"


@pytest.mark.django_db
def test_update_host_profile():
    """Test host can update their profile"""
    host_profile = HostProfileFactory()

    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    data = {"bio": "Updated host bio", "organization_name": "New Org"}

    response = client.patch("/api/accounts/host/profile/me/", data, format="json")

    assert response.status_code == status.HTTP_200_OK
    host_profile.refresh_from_db()
    assert host_profile.bio == "Updated host bio"


@pytest.mark.django_db
def test_player_cannot_update_host_profile():
    """Test player cannot update host profile"""
    player_profile = PlayerProfileFactory()

    client = APIClient()
    client.force_authenticate(user=player_profile.user)

    data = {"bio": "Hacked"}

    response = client.patch("/api/accounts/host/profile/me/", data, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_host_cannot_update_player_profile():
    """Test host cannot update player profile"""
    host_profile = HostProfileFactory()

    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    data = {"bio": "Hacked"}

    response = client.patch("/api/accounts/player/profile/me/", data, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_get_user_detail_by_id():
    """Test getting any user's public profile by ID"""
    player_profile = PlayerProfileFactory()

    client = APIClient()

    response = client.get(f"/api/accounts/users/{player_profile.user.id}/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["user"]["username"] == player_profile.user.username


@pytest.mark.django_db
def test_search_players_by_username():
    """Test searching for players by username"""
    PlayerProfileFactory(user=UserFactory(username="player1"))
    PlayerProfileFactory(user=UserFactory(username="player2"))
    PlayerProfileFactory(user=UserFactory(username="other"))

    client = APIClient()

    response = client.get("/api/accounts/players/search/?q=player")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 2


@pytest.mark.django_db
def test_search_players_minimum_query_length():
    """Test search requires minimum 2 characters"""
    PlayerProfileFactory(user=UserFactory(username="player1"))

    client = APIClient()

    response = client.get("/api/accounts/players/search/?q=p")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 0


@pytest.mark.django_db
def test_search_players_for_team_excludes_in_team():
    """Test search for team excludes players already in teams"""
    from accounts.models import Team

    # Player in team
    player1 = PlayerProfileFactory(user=UserFactory(username="player1"))
    team = Team.objects.create(name="Test Team", captain=player1.user, is_temporary=False)
    TeamMember.objects.create(team=team, user=player1.user, username=player1.user.username)

    # Player not in team
    PlayerProfileFactory(user=UserFactory(username="player2"))

    client = APIClient()

    response = client.get("/api/accounts/players/search/?q=player&for_team=true")

    assert response.status_code == status.HTTP_200_OK
    # Should only return player2
    assert len(response.data["results"]) == 1
    assert response.data["results"][0]["username"] == "player2"


@pytest.mark.django_db
def test_search_hosts_by_username():
    """Test searching for hosts by username"""
    # Explicitly set usernames that contain 'host'
    HostProfileFactory(user=UserFactory(username="host1", user_type="host"))
    HostProfileFactory(user=UserFactory(username="host2", user_type="host"))
    HostProfileFactory(user=UserFactory(username="other", user_type="host"))

    client = APIClient()

    response = client.get("/api/accounts/hosts/search/?q=host")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data["results"]) == 2


@pytest.mark.django_db
def test_username_change_limit():
    """Test username can only be changed once every 6 months"""
    from datetime import timedelta

    from django.utils import timezone

    player_profile = PlayerProfileFactory()
    user = player_profile.user

    # First change
    user.username_change_count = 1
    user.last_username_change = timezone.now() - timedelta(days=30)  # 1 month ago
    user.save()

    client = APIClient()
    client.force_authenticate(user=user)

    data = {"username": "newusername"}

    response = client.patch("/api/accounts/me/", data, format="json")

    # Should fail because not enough time has passed
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "6 months" in response.data.get("error", "").lower()


@pytest.mark.django_db
def test_username_change_allowed_after_6_months():
    """Test username can be changed after 6 months"""
    from datetime import timedelta

    from django.utils import timezone

    player_profile = PlayerProfileFactory()
    user = player_profile.user

    # Previous change was 7 months ago
    user.username_change_count = 1
    user.last_username_change = timezone.now() - timedelta(days=210)
    user.save()

    client = APIClient()
    client.force_authenticate(user=user)

    data = {"username": "newusername"}

    response = client.patch("/api/accounts/me/", data, format="json")

    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.username == "newusername"
    assert user.username_change_count == 2


@pytest.mark.django_db
def test_get_player_profile_by_id():
    """Test getting player profile by ID"""
    player_profile = PlayerProfileFactory()

    client = APIClient()
    # Authenticate to access profile
    client.force_authenticate(user=player_profile.user)

    response = client.get(f"/api/accounts/player/profile/{player_profile.id}/")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_get_host_profile_by_id():
    """Test getting host profile by ID"""
    host_profile = HostProfileFactory()

    client = APIClient()

    response = client.get(f"/api/accounts/host/profile/{host_profile.id}/")

    assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_unauthenticated_cannot_update_profile():
    """Test unauthenticated user cannot update profile"""
    client = APIClient()

    data = {"username": "hacker"}

    response = client.patch("/api/accounts/me/", data, format="json")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
