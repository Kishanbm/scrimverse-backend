"""
Extended Test cases for Team Management
Tests cover:
- Captain leaving scenarios
- Team deletion when last member leaves
- Transferring captaincy
- Adding players to team
- Team size limits
- Captain-only actions
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Team, TeamMember
from tests.factories import PlayerProfileFactory, UserFactory


@pytest.mark.django_db
def test_captain_leaves_team_with_other_members():
    """Test captain leaving team promotes next member to captain"""
    captain = UserFactory(user_type="player")
    member1 = UserFactory(user_type="player")
    member2 = UserFactory(user_type="player")

    team = Team.objects.create(name="Test Team", captain=captain)
    TeamMember.objects.create(team=team, user=captain, username=captain.username, is_captain=True)
    tm1 = TeamMember.objects.create(team=team, user=member1, username=member1.username, is_captain=False)
    TeamMember.objects.create(team=team, user=member2, username=member2.username, is_captain=False)

    client = APIClient()
    client.force_authenticate(user=captain)

    response = client.post(f"/api/accounts/teams/{team.id}/leave_team/")

    assert response.status_code == status.HTTP_200_OK

    # Team should still exist
    team.refresh_from_db()
    assert Team.objects.filter(id=team.id).exists()

    # First member should be promoted to captain
    assert team.captain == member1
    tm1.refresh_from_db()
    assert tm1.is_captain is True

    # Original captain should no longer be a member
    assert not TeamMember.objects.filter(team=team, user=captain).exists()


@pytest.mark.django_db
def test_captain_leaves_team_as_only_member():
    """Test that team is deleted when captain leaves as the only member"""
    captain = UserFactory(user_type="player")

    team = Team.objects.create(name="Solo Team", captain=captain)
    TeamMember.objects.create(team=team, user=captain, username=captain.username, is_captain=True)

    team_id = team.id

    client = APIClient()
    client.force_authenticate(user=captain)

    response = client.post(f"/api/accounts/teams/{team.id}/leave_team/")

    assert response.status_code == status.HTTP_200_OK

    # Team should be deleted
    assert not Team.objects.filter(id=team_id).exists()
    assert not TeamMember.objects.filter(team_id=team_id).exists()


@pytest.mark.django_db
def test_last_member_leaves_team_deletes_team():
    """Test that team is deleted when last member leaves"""
    captain = UserFactory(user_type="player")
    member = UserFactory(user_type="player")

    team = Team.objects.create(name="Two Member Team", captain=captain)
    TeamMember.objects.create(team=team, user=captain, username=captain.username, is_captain=True)
    TeamMember.objects.create(team=team, user=member, username=member.username, is_captain=False)

    # Captain leaves first (member becomes captain)
    client1 = APIClient()
    client1.force_authenticate(user=captain)
    response1 = client1.post(f"/api/accounts/teams/{team.id}/leave_team/")
    assert response1.status_code == status.HTTP_200_OK

    team.refresh_from_db()
    assert team.captain == member

    team_id = team.id

    # Last member leaves
    client2 = APIClient()
    client2.force_authenticate(user=member)
    response2 = client2.post(f"/api/accounts/teams/{team.id}/leave_team/")

    assert response2.status_code == status.HTTP_200_OK

    # Team should be deleted
    assert not Team.objects.filter(id=team_id).exists()


@pytest.mark.django_db
def test_transfer_captaincy_to_specific_member():
    """Test captain can transfer captaincy to a specific member"""
    captain = UserFactory(user_type="player")
    member1 = UserFactory(user_type="player")
    member2 = UserFactory(user_type="player")

    team = Team.objects.create(name="Transfer Team", captain=captain)
    captain_member = TeamMember.objects.create(team=team, user=captain, username=captain.username, is_captain=True)
    TeamMember.objects.create(team=team, user=member1, username=member1.username, is_captain=False)
    tm2 = TeamMember.objects.create(team=team, user=member2, username=member2.username, is_captain=False)

    client = APIClient()
    client.force_authenticate(user=captain)

    # Transfer to member2 (not the first member)
    response = client.post(f"/api/accounts/teams/{team.id}/transfer_captaincy/", {"member_id": tm2.id}, format="json")

    assert response.status_code == status.HTTP_200_OK

    team.refresh_from_db()
    assert team.captain == member2

    tm2.refresh_from_db()
    assert tm2.is_captain is True

    captain_member.refresh_from_db()
    assert captain_member.is_captain is False


@pytest.mark.django_db
def test_non_captain_cannot_transfer_captaincy():
    """Test that non-captain cannot transfer captaincy"""
    captain = UserFactory(user_type="player")
    member1 = UserFactory(user_type="player")
    member2 = UserFactory(user_type="player")

    team = Team.objects.create(name="Test Team", captain=captain)
    TeamMember.objects.create(team=team, user=captain, username=captain.username, is_captain=True)
    TeamMember.objects.create(team=team, user=member1, username=member1.username, is_captain=False)
    tm2 = TeamMember.objects.create(team=team, user=member2, username=member2.username, is_captain=False)

    client = APIClient()
    client.force_authenticate(user=member1)

    response = client.post(f"/api/accounts/teams/{team.id}/transfer_captaincy/", {"member_id": tm2.id}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_add_player_to_team_by_captain():
    """Test captain can add players to team"""
    captain = UserFactory(user_type="player")
    new_player = UserFactory(user_type="player")
    PlayerProfileFactory(user=new_player)

    team = Team.objects.create(name="Growing Team", captain=captain)
    TeamMember.objects.create(team=team, user=captain, username=captain.username, is_captain=True)

    client = APIClient()
    client.force_authenticate(user=captain)

    response = client.post(f"/api/accounts/teams/{team.id}/invite_player/", {"player_id": new_player.id}, format="json")

    assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
def test_cannot_add_player_when_team_full():
    """Test cannot add player when team has reached max size (15 members)"""
    captain = UserFactory(user_type="player")
    team = Team.objects.create(name="Full Team", captain=captain)
    TeamMember.objects.create(team=team, user=captain, username=captain.username, is_captain=True)

    # Add 14 more members (total 15)
    for i in range(14):
        user = UserFactory(user_type="player", username=f"member{i}")
        PlayerProfileFactory(user=user)
        TeamMember.objects.create(team=team, user=user, username=user.username)

    # Try to add 16th member
    new_player = UserFactory(user_type="player")
    PlayerProfileFactory(user=new_player)

    client = APIClient()
    client.force_authenticate(user=captain)

    response = client.post(f"/api/accounts/teams/{team.id}/invite_player/", {"player_id": new_player.id}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "full" in response.data.get("error", "").lower()


@pytest.mark.django_db
def test_captain_can_remove_member():
    """Test captain can remove a member from team"""
    captain = UserFactory(user_type="player")
    member = UserFactory(user_type="player")

    team = Team.objects.create(name="Test Team", captain=captain)
    TeamMember.objects.create(team=team, user=captain, username=captain.username, is_captain=True)
    member_obj = TeamMember.objects.create(team=team, user=member, username=member.username, is_captain=False)

    client = APIClient()
    client.force_authenticate(user=captain)

    response = client.post(f"/api/accounts/teams/{team.id}/remove_member/", {"member_id": member_obj.id}, format="json")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not TeamMember.objects.filter(id=member_obj.id).exists()


@pytest.mark.django_db
def test_non_captain_cannot_remove_member():
    """Test non-captain cannot remove members"""
    captain = UserFactory(user_type="player")
    member1 = UserFactory(user_type="player")
    member2 = UserFactory(user_type="player")

    team = Team.objects.create(name="Test Team", captain=captain)
    TeamMember.objects.create(team=team, user=captain, username=captain.username, is_captain=True)
    TeamMember.objects.create(team=team, user=member1, username=member1.username, is_captain=False)
    tm2 = TeamMember.objects.create(team=team, user=member2, username=member2.username, is_captain=False)

    client = APIClient()
    client.force_authenticate(user=member1)

    response = client.post(f"/api/accounts/teams/{team.id}/remove_member/", {"member_id": tm2.id}, format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_captain_cannot_remove_self_directly():
    """Test captain cannot remove themselves using remove_member"""
    captain = UserFactory(user_type="player")
    member = UserFactory(user_type="player")

    team = Team.objects.create(name="Test Team", captain=captain)
    captain_member = TeamMember.objects.create(team=team, user=captain, username=captain.username, is_captain=True)
    TeamMember.objects.create(team=team, user=member, username=member.username, is_captain=False)

    client = APIClient()
    client.force_authenticate(user=captain)

    response = client.post(
        f"/api/accounts/teams/{team.id}/remove_member/", {"member_id": captain_member.id}, format="json"
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "captain" in response.data.get("error", "").lower()


@pytest.mark.django_db
def test_member_can_leave_team():
    """Test regular member can leave team"""
    captain = UserFactory(user_type="player")
    member = UserFactory(user_type="player")

    team = Team.objects.create(name="Test Team", captain=captain)
    TeamMember.objects.create(team=team, user=captain, username=captain.username, is_captain=True)
    member_obj = TeamMember.objects.create(team=team, user=member, username=member.username, is_captain=False)

    client = APIClient()
    client.force_authenticate(user=member)

    response = client.post(f"/api/accounts/teams/{team.id}/leave_team/")

    assert response.status_code == status.HTTP_200_OK
    assert not TeamMember.objects.filter(id=member_obj.id).exists()

    # Team should still exist with captain
    assert Team.objects.filter(id=team.id).exists()


@pytest.mark.django_db
def test_cannot_add_player_already_in_another_team():
    """Test cannot invite player who is already in another permanent team"""
    captain1 = UserFactory(user_type="player")
    captain2 = UserFactory(user_type="player")
    player = UserFactory(user_type="player")
    PlayerProfileFactory(user=player)

    # Player is in team1
    team1 = Team.objects.create(name="Team 1", captain=captain1, is_temporary=False)
    TeamMember.objects.create(team=team1, user=captain1, username=captain1.username, is_captain=True)
    TeamMember.objects.create(team=team1, user=player, username=player.username, is_captain=False)

    # Captain2 tries to invite player to team2
    team2 = Team.objects.create(name="Team 2", captain=captain2, is_temporary=False)
    TeamMember.objects.create(team=team2, user=captain2, username=captain2.username, is_captain=True)

    client = APIClient()
    client.force_authenticate(user=captain2)

    response = client.post(f"/api/accounts/teams/{team2.id}/invite_player/", {"player_id": player.id}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already" in response.data.get("error", "").lower()


@pytest.mark.django_db
def test_team_deletion_cascade():
    """Test that team deletion cascades properly to members and join requests"""
    from accounts.models import TeamJoinRequest

    captain = UserFactory(user_type="player")
    member = UserFactory(user_type="player")
    requesting_player = UserFactory(user_type="player")
    PlayerProfileFactory(user=requesting_player)

    team = Team.objects.create(name="Delete Team", captain=captain)
    TeamMember.objects.create(team=team, user=captain, username=captain.username, is_captain=True)
    TeamMember.objects.create(team=team, user=member, username=member.username, is_captain=False)

    # Create a join request
    TeamJoinRequest.objects.create(team=team, player=requesting_player, request_type="request", status="pending")

    team_id = team.id

    # Delete team
    team.delete()

    # Verify cascade deletion
    assert not Team.objects.filter(id=team_id).exists()
    assert not TeamMember.objects.filter(team_id=team_id).exists()
    assert not TeamJoinRequest.objects.filter(team_id=team_id).exists()
