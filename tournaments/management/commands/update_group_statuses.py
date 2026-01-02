"""
Management command to update group statuses based on match completion
"""
from django.core.management.base import BaseCommand

from tournaments.models import Group


class Command(BaseCommand):
    help = "Update group statuses based on match completion"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tournament-id",
            type=int,
            help="Tournament ID to update groups for",
        )
        parser.add_argument(
            "--round-number",
            type=int,
            help="Round number to update groups for",
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

        updated_count = 0
        for group in groups:
            total_matches = group.matches.count()
            completed_matches = group.matches.filter(status="completed").count()

            # Check if all completed matches have scores
            completed_matches_with_scores = 0
            for match in group.matches.filter(status="completed"):
                if match.scores.exists():
                    completed_matches_with_scores += 1

            self.stdout.write(
                f"Group {group.group_name}: {completed_matches}/{total_matches} matches completed, "
                f"{completed_matches_with_scores} with scores"
            )

            # Update status
            if (
                total_matches > 0
                and completed_matches == total_matches
                and completed_matches_with_scores == total_matches
            ):
                if group.status != "completed":
                    group.status = "completed"
                    group.save(update_fields=["status"])
                    updated_count += 1
                    self.stdout.write(self.style.SUCCESS(f"✓ Updated {group.group_name} to completed"))
            elif completed_matches > 0:
                if group.status != "ongoing":
                    group.status = "ongoing"
                    group.save(update_fields=["status"])
                    updated_count += 1
                    self.stdout.write(self.style.SUCCESS(f"✓ Updated {group.group_name} to ongoing"))

        self.stdout.write(self.style.SUCCESS(f"\nUpdated {updated_count} groups"))
