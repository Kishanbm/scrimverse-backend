from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import HostProfile, PlayerProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "username", "user_type", "is_staff", "created_at")
    list_filter = ("user_type", "is_staff", "is_active")
    search_fields = ("email", "username")
    ordering = ("-created_at",)

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Custom Fields", {"fields": ("user_type", "phone_number", "profile_picture")}),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Custom Fields", {"fields": ("email", "user_type", "phone_number")}),
    )


@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "total_tournaments_participated", "total_wins", "wallet_balance")
    search_fields = ("user__username", "user__email")
    list_filter = ("skill_level",)


@admin.register(HostProfile)
class HostProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "total_tournaments_hosted", "rating", "verified")
    list_display_links = ("user",)
    list_editable = ("verified",)
    search_fields = ("user__email", "user__username")
    list_filter = ("verified", "rating")
    actions = ["verify_hosts", "unverify_hosts"]

    def verify_hosts(self, request, queryset):
        queryset.update(verified=True)

    verify_hosts.short_description = "Verify selected hosts"

    def unverify_hosts(self, request, queryset):
        queryset.update(verified=False)

    unverify_hosts.short_description = "Unverify selected hosts"
