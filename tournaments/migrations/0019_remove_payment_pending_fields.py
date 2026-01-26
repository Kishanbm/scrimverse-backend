# Generated migration to remove is_payment_pending fields

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("tournaments", "0018_tournament_is_payment_pending_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="tournament",
            name="is_payment_pending",
        ),
        migrations.RemoveField(
            model_name="tournament",
            name="payment_deadline",
        ),
        migrations.RemoveField(
            model_name="tournamentregistration",
            name="is_payment_pending",
        ),
        migrations.RemoveField(
            model_name="tournamentregistration",
            name="payment_deadline",
        ),
    ]
