import pytest
from rest_framework import status
from rest_framework.test import APIClient

from tests.factories import HostProfileFactory, TournamentFactory, TournamentRegistrationFactory
from tournaments.models import Group, Match, MatchScore


@pytest.fixture
def host_client():
    host_profile = HostProfileFactory()
    client = APIClient()
    client.force_authenticate(user=host_profile.user)
    return client, host_profile


@pytest.mark.django_db
def test_configure_round_success(host_client):
    """Test host can configure a tournament round"""
    client, host_profile = host_client
    tournament = TournamentFactory(
        host=host_profile, status="upcoming", rounds=[{"round": 1, "max_teams": 100, "qualifying_teams": 50}]
    )

    # Create 4 registrations
    for _ in range(4):
        TournamentRegistrationFactory(tournament=tournament, status="confirmed")

    # Set current round to 0 (initial)
    tournament.current_round = 0
    tournament.save()

    data = {"teams_per_group": 2, "qualifying_per_group": 1, "matches_per_group": 2}

    response = client.post(f"/api/tournaments/{tournament.id}/rounds/1/configure/", data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert Group.objects.filter(tournament=tournament, round_number=1).count() == 2
    assert Match.objects.filter(group__tournament=tournament).count() == 4


@pytest.mark.django_db
def test_submit_match_scores(host_client):
    """Test host can submit match scores"""
    client, host_profile = host_client
    tournament = TournamentFactory(host=host_profile)
    group = Group.objects.create(tournament=tournament, round_number=1, group_name="Group 1")
    match = Match.objects.create(group=group, match_number=1, status="completed")

    reg1 = TournamentRegistrationFactory(tournament=tournament)
    reg2 = TournamentRegistrationFactory(tournament=tournament)

    # Add teams to group
    group.teams.add(reg1, reg2)

    data = {
        "scores": [
            {"team_id": reg1.id, "wins": 1, "position_points": 10, "kill_points": 5},
            {"team_id": reg2.id, "wins": 0, "position_points": 5, "kill_points": 2},
        ]
    }

    response = client.post(f"/api/tournaments/{tournament.id}/matches/{match.id}/scores/", data, format="json")

    assert response.status_code == status.HTTP_200_OK
    assert MatchScore.objects.filter(match=match).count() == 2

    # Check if match status is updated to completed
    match.refresh_from_db()
    assert match.status == "completed"


@pytest.mark.django_db
def test_get_round_results(host_client):
    """Test getting results for a round"""
    client, host_profile = host_client
    tournament = TournamentFactory(host=host_profile, rounds=[{"round": 1, "max_teams": 100, "qualifying_teams": 50}])
    group = Group.objects.create(tournament=tournament, round_number=1, group_name="Group 1", status="completed")
    match = Match.objects.create(group=group, match_number=1, status="completed")

    reg1 = TournamentRegistrationFactory(tournament=tournament)
    group.teams.add(reg1)
    MatchScore.objects.create(match=match, team=reg1, position_points=10, kill_points=5, total_points=15)

    response = client.get(f"/api/tournaments/{tournament.id}/rounds/1/results/")

    assert response.status_code == status.HTTP_200_OK
    assert "results" in response.data
    assert len(response.data["results"]) > 0


@pytest.mark.django_db
def test_start_match(host_client):
    """Test starting a match with room ID and password"""
    client, host_profile = host_client
    tournament = TournamentFactory(host=host_profile)
    group = Group.objects.create(tournament=tournament, round_number=1, group_name="Group 1")
    match = Match.objects.create(group=group, match_number=1, status="waiting")

    data = {"match_number": 1, "match_id": "ROOM_123", "match_password": "PASS_123"}

    response = client.post(f"/api/tournaments/{tournament.id}/groups/{group.id}/matches/start/", data, format="json")

    assert response.status_code == status.HTTP_200_OK
    match.refresh_from_db()
    assert match.match_id == "ROOM_123"
    assert match.match_password == "PASS_123"
    assert match.status == "ongoing"
