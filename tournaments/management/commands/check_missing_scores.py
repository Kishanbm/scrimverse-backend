"""
Management command to check which matches are missing scores
"""
from django.core.management.base import BaseCommand

from tournaments.models import Group


class Command(BaseCommand):
    help = "Check which matches are missing scores"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tournament-id",
            type=int,
            help="Tournament ID to check",
        )
        parser.add_argument(
            "--round-number",
            type=int,
            help="Round number to check",
        )

    def handle(self, *args, **options):
        tournament_id = options.get("tournament_id")
        round_number = options.get("round_number")

        if tournament_id and round_number:
            groups = Group.objects.filter(tournament_id=tournament_id, round_number=round_number)
        elif tournament_id:
            groups = Group.objects.filter(tournament_id=tournament_id)
        else:
            groups = Group.objects.all()

        for group in groups:
            self.stdout.write(
                f"\n{group.group_name} (Tournament: {group.tournament.title}, Round {group.round_number})"
            )
            self.stdout.write("-" * 60)

            for match in group.matches.all().order_by("match_number"):
                scores_count = match.scores.count()
                status_color = self.style.SUCCESS if match.status == "completed" else self.style.WARNING

                if match.status == "completed" and scores_count == 0:
                    self.stdout.write(
                        self.style.ERROR(
                            f"  Match {match.match_number}: {match.status.upper()} - "
                            f"⚠️  NO SCORES ({scores_count} teams scored)"
                        )
                    )
                else:
                    self.stdout.write(
                        status_color(
                            f"  Match {match.match_number}: {match.status.upper()} - " f"{scores_count} teams scored"
                        )
                    )
