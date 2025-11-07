"""
Django management command to update tournament statuses based on time
Run this periodically (every minute) via cron or scheduler
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from tournaments.models import Tournament


class Command(BaseCommand):
    help = "Update tournament statuses based on current time"

    def handle(self, *args, **options):
        now = timezone.now()

        # Update to ongoing
        updated_ongoing = Tournament.objects.filter(
            tournament_start__lte=now, tournament_end__gt=now, status="upcoming"
        ).update(status="ongoing")

        # Update to completed
        updated_completed = Tournament.objects.filter(
            tournament_end__lte=now, status__in=["upcoming", "ongoing"]
        ).update(status="completed")

        if updated_ongoing > 0:
            self.stdout.write(self.style.SUCCESS(f"✓ Updated {updated_ongoing} tournament(s) to ONGOING"))

        if updated_completed > 0:
            self.stdout.write(self.style.SUCCESS(f"✓ Updated {updated_completed} tournament(s) to COMPLETED"))

        if updated_ongoing == 0 and updated_completed == 0:
            self.stdout.write(self.style.SUCCESS("✓ All tournament statuses are up-to-date"))

        # Also clear cache
        from django.core.cache import cache

        cache.delete("tournaments:list:all")
        self.stdout.write(self.style.SUCCESS("✓ Cache cleared"))
