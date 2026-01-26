"""
Comprehensive tests for Tournament Views
Tests cover all tournament CRUD operations, registration, and management
"""
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from tests.factories import HostProfileFactory, PlayerProfileFactory, TournamentFactory, TournamentRegistrationFactory
from tournaments.models import Tournament, TournamentRegistration


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


def get_results(data):
    """Helper to handle paginated vs non-paginated responses"""
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


@pytest.mark.django_db
def test_list_tournaments_public():
    """Test that anyone can list tournaments"""
    HostProfileFactory()
    TournamentFactory.create_batch(5)

    client = APIClient()
    response = client.get("/api/tournaments/")

    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    assert len(results) >= 5


@pytest.mark.django_db
def test_get_tournament_detail_public():
    """Test that anyone can view tournament details"""
    tournament = TournamentFactory()

    client = APIClient()
    response = client.get(f"/api/tournaments/{tournament.id}/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == tournament.title


@pytest.mark.django_db
def test_create_tournament_as_host():
    """Test host can create tournament"""
    host_profile = HostProfileFactory()

    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    future_time = timezone.now() + timedelta(days=7)
    data = {
        "title": "New Tournament Unique",
        "description": "Test tournament",
        "game_name": "BGMI",
        "event_mode": "TOURNAMENT",
        "game_mode": "Squad",
        "max_participants": 100,
        "tournament_date": (future_time.date()).isoformat(),
        "tournament_time": (future_time.time()).isoformat(),
        "tournament_start": future_time.isoformat(),
        "tournament_end": (future_time + timedelta(hours=3)).isoformat(),
        "registration_start": (timezone.now() - timedelta(hours=1)).isoformat(),
        "registration_end": (future_time - timedelta(hours=1)).isoformat(),
        "entry_fee": 0,
        "prize_pool": 10000,
        "rules": "Follow the rules please.",
        "plan_type": "basic",
        "rounds": [{"round": 1, "max_teams": 100, "qualifying_teams": 50}],
    }

    response = client.post("/api/tournaments/create/", data, format="json")

    if response.status_code == 400:
        print(f"DEBUG: Create tournament failed: {response.data}")

    assert response.status_code == status.HTTP_200_OK
    assert Tournament.objects.filter(title="New Tournament Unique").exists()


@pytest.mark.django_db
def test_create_tournament_as_player_fails():
    """Test player cannot create tournament"""
    player_profile = PlayerProfileFactory()

    client = APIClient()
    client.force_authenticate(user=player_profile.user)

    future_time = timezone.now() + timedelta(days=7)
    data = {
        "title": "New Tournament",
        "game_name": "BGMI",
        "max_participants": 100,
        "tournament_start": future_time.isoformat(),
    }

    response = client.post("/api/tournaments/create/", data, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_update_tournament_as_host():
    """Test host can update their tournament"""
    host_profile = HostProfileFactory()
    tournament = TournamentFactory(host=host_profile)

    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    data = {"title": "Updated Title Unique", "description": "Updated description"}

    response = client.patch(f"/api/tournaments/{tournament.id}/update/", data, format="json")

    assert response.status_code == status.HTTP_200_OK
    tournament.refresh_from_db()
    assert tournament.title == "Updated Title Unique"


@pytest.mark.django_db
def test_update_tournament_as_other_host_fails():
    """Test host cannot update another host's tournament"""
    host1 = HostProfileFactory()
    host2 = HostProfileFactory()
    tournament = TournamentFactory(host=host1)

    client = APIClient()
    client.force_authenticate(user=host2.user)

    data = {"title": "Hacked Title"}

    response = client.patch(f"/api/tournaments/{tournament.id}/update/", data, format="json")

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
def test_delete_tournament_as_host():
    """Test host can delete their tournament"""
    host_profile = HostProfileFactory()
    tournament = TournamentFactory(host=host_profile)
    tournament_id = tournament.id

    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    response = client.delete(f"/api/tournaments/{tournament.id}/delete/")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Tournament.objects.filter(id=tournament_id).exists()


@pytest.mark.django_db
def test_register_for_tournament_as_player():
    """Test player can register for tournament"""
    host_profile = HostProfileFactory()
    now = timezone.now()
    tournament = TournamentFactory(
        host=host_profile,
        game_mode="Solo",
        entry_fee=0,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=1),
    )
    player_profile = PlayerProfileFactory()

    client = APIClient()
    client.force_authenticate(user=player_profile.user)

    data = {"team_name": "My Team", "player_usernames": [player_profile.user.username]}

    response = client.post(f"/api/tournaments/{tournament.id}/register/", data, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert TournamentRegistration.objects.filter(tournament=tournament, player=player_profile).exists()


@pytest.mark.django_db
def test_cannot_register_twice_for_same_tournament():
    """Test player cannot register twice for the same tournament"""
    host_profile = HostProfileFactory()
    now = timezone.now()
    tournament = TournamentFactory(
        host=host_profile,
        game_mode="Solo",
        entry_fee=0,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=1),
    )
    player_profile = PlayerProfileFactory()

    # First registration
    TournamentRegistrationFactory(tournament=tournament, player=player_profile)

    client = APIClient()
    client.force_authenticate(user=player_profile.user)

    data = {"team_name": "Another Team", "player_usernames": [player_profile.user.username]}

    response = client.post(f"/api/tournaments/{tournament.id}/register/", data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_cannot_register_for_full_tournament():
    """Test cannot register when tournament is full"""
    host_profile = HostProfileFactory()
    now = timezone.now()
    tournament = TournamentFactory(
        host=host_profile,
        game_mode="Solo",
        max_participants=1,
        entry_fee=0,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=1),
    )
    # Create one registration to fill it
    TournamentRegistrationFactory(tournament=tournament)

    player_profile = PlayerProfileFactory()

    client = APIClient()
    client.force_authenticate(user=player_profile.user)

    data = {"team_name": "My Team", "player_usernames": [player_profile.user.username]}

    response = client.post(f"/api/tournaments/{tournament.id}/register/", data, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_get_tournament_registrations_as_host():
    """Test host can view registrations for their tournament"""
    host_profile = HostProfileFactory()
    tournament = TournamentFactory(host=host_profile)
    TournamentRegistrationFactory.create_batch(3, tournament=tournament)

    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    response = client.get(f"/api/tournaments/{tournament.id}/registrations/")

    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    assert len(results) >= 3


@pytest.mark.django_db
def test_filter_tournaments_by_game():
    """Test filtering tournaments by game"""
    TournamentFactory(game_name="BGMI_UNIQUE")
    TournamentFactory(game_name="BGMI_UNIQUE")
    TournamentFactory(game_name="VALORANT_UNIQUE")

    client = APIClient()
    response = client.get("/api/tournaments/?game=BGMI_UNIQUE")

    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    match_count = sum(1 for t in results if "BGMI_UNIQUE" in t["game_name"])
    assert match_count == 2


@pytest.mark.django_db
def test_filter_tournaments_by_status():
    """Test filtering tournaments by status"""
    TournamentFactory(status="upcoming", title="StatusCheck1")
    TournamentFactory(status="ongoing", title="StatusCheck2")

    client = APIClient()
    response = client.get("/api/tournaments/?status=upcoming")

    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    for tournament in results:
        if tournament["title"].startswith("StatusCheck"):
            assert tournament["status"] == "upcoming"


@pytest.mark.django_db
def test_search_tournaments():
    """Test searching tournaments by title"""
    TournamentFactory(title="UniqueSearch1")
    TournamentFactory(title="UniqueSearch2")
    TournamentFactory(title="OtherTitle")

    client = APIClient()
    response = client.get("/api/tournaments/?search=UniqueSearch")

    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    match_count = sum(1 for t in results if "UniqueSearch" in t["title"])
    assert match_count == 2


@pytest.mark.django_db
def test_get_my_registrations_as_player():
    """Test player can view tournaments they're registered for"""
    player_profile = PlayerProfileFactory()
    tournament1 = TournamentFactory(title="MyReg1")
    tournament2 = TournamentFactory(title="MyReg2")

    TournamentRegistrationFactory(tournament=tournament1, player=player_profile)
    TournamentRegistrationFactory(tournament=tournament2, player=player_profile)

    client = APIClient()
    client.force_authenticate(user=player_profile.user)

    response = client.get("/api/tournaments/my-registrations/")

    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    match_count = sum(1 for r in results if r["tournament"]["title"].startswith("MyReg"))
    assert match_count == 2


@pytest.mark.django_db
def test_get_host_tournaments():
    """Test getting tournaments by host"""
    host_profile = HostProfileFactory()
    TournamentFactory.create_batch(3, host=host_profile, title="HostTrn")

    client = APIClient()

    response = client.get(f"/api/tournaments/host/{host_profile.id}/")

    assert response.status_code == status.HTTP_200_OK
    results = get_results(response.data)
    match_count = sum(1 for t in results if t["title"].startswith("HostTrn"))
    assert match_count == 3
