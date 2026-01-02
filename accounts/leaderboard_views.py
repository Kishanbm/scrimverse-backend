"""
Leaderboard API views
"""
from django.core.cache import cache

from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.models import TeamStatistics
from accounts.serializers import TeamStatisticsSerializer


class LeaderboardView(generics.GenericAPIView):
    """
    Get top teams leaderboard
    GET /api/leaderboard/?limit=50
    """

    permission_classes = [AllowAny]

    def get(self, request):
        limit = int(request.query_params.get("limit", 50))

        # Try to get from cache first
        cache_key = f"leaderboard:top{limit}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data)

        # Get top teams
        top_teams = TeamStatistics.objects.select_related("team").filter(rank__gt=0, rank__lte=limit).order_by("rank")

        serializer = TeamStatisticsSerializer(top_teams, many=True)
        data = {"leaderboard": serializer.data, "total_teams": TeamStatistics.objects.filter(rank__gt=0).count()}

        # Cache for 5 minutes
        cache.set(cache_key, data, 300)

        return Response(data)


class TeamRankView(generics.GenericAPIView):
    """
    Get specific team's rank and statistics
    GET /api/teams/<team_id>/rank/
    """

    permission_classes = [AllowAny]

    def get(self, request, team_id):
        try:
            stats = TeamStatistics.objects.select_related("team").get(team_id=team_id)
            serializer = TeamStatisticsSerializer(stats)
            return Response(serializer.data)
        except TeamStatistics.DoesNotExist:
            return Response(
                {
                    "rank": 0,
                    "tournament_wins": 0,
                    "total_position_points": 0,
                    "total_kill_points": 0,
                    "total_points": 0,
                    "message": "No statistics available for this team",
                }
            )
