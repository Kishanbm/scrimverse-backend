"""
Celery tasks for tournaments app
"""
from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone

from celery import shared_task

from accounts.models import Team, TeamStatistics

from .models import MatchScore, Tournament, TournamentRegistration


@shared_task
def update_tournament_statuses():
    """
    Update tournament statuses based on current time
    Runs every minute via Celery Beat
    """
    now = timezone.now()

    # Update to ongoing
    updated_ongoing = Tournament.objects.filter(
        tournament_start__lte=now, tournament_end__gt=now, status="upcoming"
    ).update(status="ongoing")

    # Update to completed
    updated_completed = Tournament.objects.filter(tournament_end__lte=now, status__in=["upcoming", "ongoing"]).update(
        status="completed"
    )

    # Clear cache if any updates occurred
    if updated_ongoing > 0 or updated_completed > 0:
        cache.delete("tournaments:list:all")

    return {
        "updated_ongoing": updated_ongoing,
        "updated_completed": updated_completed,
        "timestamp": now.isoformat(),
    }


@shared_task
def update_leaderboard():
    """
    Update team leaderboard statistics
    Called when a tournament is completed
    Calculates:
    - Tournament wins (1st place finishes only)
    - Total position points (sum across all matches)
    - Total kill points (sum across all matches)
    - Global rank (based on total points)
    """
    from django.db import transaction

    # Get all non-temporary teams
    teams = Team.objects.filter(is_temporary=False)

    for team in teams:
        # Get or create statistics
        stats, created = TeamStatistics.objects.get_or_create(team=team)

        # Count tournament wins (1st place finishes in completed tournaments)
        tournament_wins = 0
        completed_tournaments = Tournament.objects.filter(status="completed")

        for tournament in completed_tournaments:
            # Get final standings for this tournament
            try:
                # Get all registrations for this tournament
                registrations = TournamentRegistration.objects.filter(tournament=tournament, team=team)

                if registrations.exists():
                    # registration = registrations.first()  # noqa: F841
                    # Check if this team won (rank 1 in final standings)
                    # We need to calculate final rank based on total points
                    final_round = tournament.current_round
                    if final_round > 0:
                        # Get all scores for this team in the final round
                        # team_scores = MatchScore.objects.filter(  # noqa: F841
                        #     team__team=team,
                        #     match__group__tournament=tournament,
                        #     match__group__round_number=final_round
                        # ).aggregate(total_pos=Sum("position_points"), total_kills=Sum("kill_points"))

                        # team_total = (team_scores["total_pos"] or 0)  # noqa: F841
                        # team_total += (team_scores["total_kills"] or 0)

                        # Get all teams' totals for this tournament
                        all_teams_scores = (
                            MatchScore.objects.filter(
                                match__group__tournament=tournament, match__group__round_number=final_round
                            )
                            .values("team__team")
                            .annotate(total=Sum("position_points") + Sum("kill_points"))
                            .order_by("-total")
                        )

                        # Check if this team is rank 1
                        if all_teams_scores and all_teams_scores[0]["team__team"] == team.id:
                            tournament_wins += 1
            except Exception as e:
                print(f"Error calculating tournament win for team {team.name}: {e}")
                continue

        # Calculate total points from ALL matches (not just completed tournaments)
        all_scores = MatchScore.objects.filter(team__team=team).aggregate(
            total_position=Sum("position_points"), total_kills=Sum("kill_points")
        )

        # Update statistics
        stats.tournament_wins = tournament_wins
        stats.total_position_points = all_scores["total_position"] or 0
        stats.total_kill_points = all_scores["total_kills"] or 0
        stats.update_total_points()

    # Assign ranks based on total points (descending)
    all_stats = TeamStatistics.objects.all().order_by("-total_points", "-tournament_wins", "-total_kill_points")

    with transaction.atomic():
        for rank, stat in enumerate(all_stats, start=1):
            stat.rank = rank
            stat.save(update_fields=["rank"])

    # Clear leaderboard cache
    cache.delete("leaderboard:top50")

    return {"teams_updated": teams.count(), "timestamp": timezone.now().isoformat()}
