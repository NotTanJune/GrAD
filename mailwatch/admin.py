# mailwatch/admin.py
from django.contrib import admin
from .models import EmailAccount, Notification


@admin.register(EmailAccount)
class EmailAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "email_address", "active", "created_at")
    list_filter = ("provider", "active", "created_at")
    search_fields = ("email_address", "user__username", "user__email")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "application",
        "source",
        "subject",
        "sender",
        "sent_at",
        "is_read",
        "created_at",
    )
    list_filter = ("source", "is_read", "created_at")
    search_fields = ("subject", "sender", "external_message_id")
    raw_id_fields = ("application",)
