# Generated migration for tournament plans

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tournaments", "0005_roundscore"),
    ]

    operations = [
        migrations.AddField(
            model_name="tournament",
            name="plan_type",
            field=models.CharField(
                choices=[
                    ("basic", "Basic Listing - ₹299"),
                    ("featured", "Featured Listing - ₹499"),
                    ("premium", "Premium + Promotion - ₹799"),
                ],
                default="basic",
                max_length=20,
                help_text="Tournament plan type",
            ),
        ),
        migrations.AddField(
            model_name="tournament",
            name="plan_price",
            field=models.DecimalField(decimal_places=2, default=299.00, max_digits=10, help_text="Plan price in INR"),
        ),
        migrations.AddField(
            model_name="tournament",
            name="plan_payment_status",
            field=models.BooleanField(default=False, help_text="Whether plan payment is completed"),
        ),
        migrations.AddField(
            model_name="tournament",
            name="plan_payment_id",
            field=models.CharField(blank=True, max_length=100, help_text="Payment transaction ID for plan"),
        ),
        migrations.AddField(
            model_name="tournament",
            name="homepage_banner",
            field=models.BooleanField(default=False, help_text="Show on homepage banner (Featured and Premium plans)"),
        ),
        migrations.AddField(
            model_name="tournament",
            name="promotional_content",
            field=models.TextField(blank=True, help_text="Custom promotional content (Premium plan only)"),
        ),
        migrations.AddField(
            model_name="tournament",
            name="visibility_boost_end",
            field=models.DateTimeField(
                blank=True, null=True, help_text="Extended visibility period end date (Premium plan)"
            ),
        ),
    ]
