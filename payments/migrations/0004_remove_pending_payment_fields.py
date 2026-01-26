# Generated migration to remove pending payment fields

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0003_payment_payment_expires_at_payment_pending_data"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="payment",
            name="pending_data",
        ),
        migrations.RemoveField(
            model_name="payment",
            name="payment_expires_at",
        ),
    ]
