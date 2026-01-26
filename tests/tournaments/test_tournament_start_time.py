"""
Test cases for Tournament Start Time Validation
Tests cover:
- Tournament cannot start before scheduled start time
- Tournament can start after scheduled start time
- Edge cases for start time validation
"""
from datetime import timedelta

from django.utils import timezone

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from tests.factories import HostProfileFactory, TournamentFactory


@pytest.mark.django_db
def test_cannot_start_tournament_before_start_time():
    """Test that tournament cannot be started before scheduled start time"""
    host_profile = HostProfileFactory()

    # Tournament starts 2 hours in the future
    future_time = timezone.now() + timedelta(hours=2)
    tournament = TournamentFactory(host=host_profile, status="upcoming", tournament_start=future_time)

    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    response = client.post(f"/api/tournaments/{tournament.id}/start/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "cannot start tournament early" in response.data.get("error", "").lower()

    # Tournament should still be upcoming
    tournament.refresh_from_db()
    assert tournament.status == "upcoming"


@pytest.mark.django_db
def test_can_start_tournament_after_start_time():
    """Test that tournament can be started after scheduled start time"""
    host_profile = HostProfileFactory()

    # Tournament was scheduled to start 1 hour ago
    past_time = timezone.now() - timedelta(hours=1)
    tournament = TournamentFactory(host=host_profile, status="upcoming", tournament_start=past_time)

    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    response = client.post(f"/api/tournaments/{tournament.id}/start/")

    assert response.status_code == status.HTTP_200_OK

    tournament.refresh_from_db()
    assert tournament.status == "ongoing"
    assert tournament.current_round == 1


@pytest.mark.django_db
def test_can_start_tournament_exactly_at_start_time():
    """Test that tournament can be started exactly at scheduled start time"""
    host_profile = HostProfileFactory()

    # Tournament starts now (within a few seconds tolerance)
    now = timezone.now()
    tournament = TournamentFactory(host=host_profile, status="upcoming", tournament_start=now)

    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    response = client.post(f"/api/tournaments/{tournament.id}/start/")

    assert response.status_code == status.HTTP_200_OK

    tournament.refresh_from_db()
    assert tournament.status == "ongoing"


@pytest.mark.django_db
def test_start_time_validation_message_includes_scheduled_time():
    """Test that error message includes the scheduled start time"""
    host_profile = HostProfileFactory()

    future_time = timezone.now() + timedelta(hours=3)
    tournament = TournamentFactory(host=host_profile, status="upcoming", tournament_start=future_time)

    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    response = client.post(f"/api/tournaments/{tournament.id}/start/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    # Error message should include the scheduled start time
    assert "scheduled start" in response.data.get("error", "").lower()


@pytest.mark.django_db
def test_cannot_start_already_ongoing_tournament():
    """Test that ongoing tournament cannot be started again"""
    host_profile = HostProfileFactory()

    past_time = timezone.now() - timedelta(hours=1)
    tournament = TournamentFactory(host=host_profile, status="ongoing", tournament_start=past_time, current_round=1)

    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    response = client.post(f"/api/tournaments/{tournament.id}/start/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "current status" in response.data.get("error", "").lower()


@pytest.mark.django_db
def test_cannot_start_completed_tournament():
    """Test that completed tournament cannot be started"""
    host_profile = HostProfileFactory()

    past_time = timezone.now() - timedelta(hours=5)
    tournament = TournamentFactory(host=host_profile, status="completed", tournament_start=past_time)

    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    response = client.post(f"/api/tournaments/{tournament.id}/start/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_start_button_disabled_before_start_time_in_frontend():
    """Test that tournament data indicates if it can be started (for frontend)"""
    host_profile = HostProfileFactory()

    future_time = timezone.now() + timedelta(hours=1)
    tournament = TournamentFactory(host=host_profile, status="upcoming", tournament_start=future_time)

    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    # Get tournament details
    response = client.get(f"/api/tournaments/{tournament.id}/manage/")

    assert response.status_code == status.HTTP_200_OK

    # Check if tournament data includes start time info
    tournament_data = response.data.get("tournament", {})
    assert "tournament_start" in tournament_data

    # Frontend can use this to disable/enable start button


@pytest.mark.django_db
def test_start_tournament_one_minute_before_start_time():
    """Test starting tournament 1 minute before scheduled time fails"""
    host_profile = HostProfileFactory()

    # Tournament starts in 1 minute
    future_time = timezone.now() + timedelta(minutes=1)
    tournament = TournamentFactory(host=host_profile, status="upcoming", tournament_start=future_time)

    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    response = client.post(f"/api/tournaments/{tournament.id}/start/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_start_tournament_one_minute_after_start_time():
    """Test starting tournament 1 minute after scheduled time succeeds"""
    host_profile = HostProfileFactory()

    # Tournament was scheduled 1 minute ago
    past_time = timezone.now() - timedelta(minutes=1)
    tournament = TournamentFactory(host=host_profile, status="upcoming", tournament_start=past_time)

    client = APIClient()
    client.force_authenticate(user=host_profile.user)

    response = client.post(f"/api/tournaments/{tournament.id}/start/")

    assert response.status_code == status.HTTP_200_OK

    tournament.refresh_from_db()
    assert tournament.status == "ongoing"


@pytest.mark.django_db
def test_only_host_can_start_tournament():
    """Test that only the tournament host can start the tournament"""
    host_profile = HostProfileFactory()
    other_host_profile = HostProfileFactory()

    past_time = timezone.now() - timedelta(hours=1)
    tournament = TournamentFactory(host=host_profile, status="upcoming", tournament_start=past_time)

    client = APIClient()
    client.force_authenticate(user=other_host_profile.user)

    response = client.post(f"/api/tournaments/{tournament.id}/start/")

    # Should return 404 (tournament not found for this host) or 403 (forbidden)
    assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
def test_player_cannot_start_tournament():
    """Test that players cannot start tournaments"""
    from tests.factories import PlayerProfileFactory

    host_profile = HostProfileFactory()
    player_profile = PlayerProfileFactory()

    past_time = timezone.now() - timedelta(hours=1)
    tournament = TournamentFactory(host=host_profile, status="upcoming", tournament_start=past_time)

    client = APIClient()
    client.force_authenticate(user=player_profile.user)

    response = client.post(f"/api/tournaments/{tournament.id}/start/")

    assert response.status_code == status.HTTP_403_FORBIDDEN
