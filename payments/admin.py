from django.contrib import admin

from .models import Payment, Refund


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin interface for Payment model"""

    list_display = [
        "merchant_order_id",
        "payment_type",
        "amount",
        "user",
        "status",
        "payment_mode",
        "created_at",
    ]
    list_filter = ["payment_type", "status", "payment_mode", "created_at"]
    search_fields = [
        "merchant_order_id",
        "phonepe_order_id",
        "phonepe_transaction_id",
        "user__username",
        "user__email",
    ]
    readonly_fields = [
        "merchant_order_id",
        "phonepe_order_id",
        "phonepe_transaction_id",
        "amount_paisa",
        "redirect_url",
        "callback_data",
        "created_at",
        "updated_at",
        "completed_at",
    ]
    fieldsets = (
        (
            "Payment Identification",
            {
                "fields": (
                    "merchant_order_id",
                    "phonepe_order_id",
                    "phonepe_transaction_id",
                )
            },
        ),
        (
            "Payment Details",
            {
                "fields": (
                    "payment_type",
                    "amount",
                    "amount_paisa",
                    "status",
                    "payment_mode",
                    "instrument_type",
                )
            },
        ),
        (
            "User Information",
            {
                "fields": (
                    "user",
                    "player_profile",
                    "host_profile",
                )
            },
        ),
        (
            "Related Objects",
            {
                "fields": (
                    "tournament",
                    "registration",
                )
            },
        ),
        (
            "PhonePe Response",
            {
                "fields": (
                    "redirect_url",
                    "callback_data",
                    "error_code",
                    "detailed_error_code",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "meta_info",
                    "created_at",
                    "updated_at",
                    "completed_at",
                )
            },
        ),
    )
    ordering = ["-created_at"]


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    """Admin interface for Refund model"""

    list_display = [
        "merchant_refund_id",
        "payment",
        "amount",
        "status",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = [
        "merchant_refund_id",
        "phonepe_refund_id",
        "payment__merchant_order_id",
    ]
    readonly_fields = [
        "merchant_refund_id",
        "phonepe_refund_id",
        "amount_paisa",
        "callback_data",
        "created_at",
        "updated_at",
        "completed_at",
    ]
    fieldsets = (
        (
            "Refund Identification",
            {
                "fields": (
                    "merchant_refund_id",
                    "phonepe_refund_id",
                )
            },
        ),
        (
            "Refund Details",
            {
                "fields": (
                    "payment",
                    "amount",
                    "amount_paisa",
                    "reason",
                    "status",
                )
            },
        ),
        (
            "PhonePe Response",
            {
                "fields": (
                    "callback_data",
                    "error_code",
                    "detailed_error_code",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "completed_at",
                )
            },
        ),
    )
    ordering = ["-created_at"]
