# mailwatch/models.py
from __future__ import annotations
from django.conf import settings
from django.db import models


class EmailAccount(models.Model):
    PROVIDER_CHOICES = [
        ("google", "Google / Gmail"),
        ("microsoft", "Microsoft / Outlook"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES)
    email_address = models.EmailField(blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "provider")

    def __str__(self):
        return f"{self.user} – {self.get_provider_display()}"


class Notification(models.Model):
    SOURCE_CHOICES = [
        ("gmail", "Gmail"),
        ("outlook", "Outlook"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # 👇 add a unique related_name to avoid clashing with applications.Notification
    application = models.ForeignKey(
        "applications.Application",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="mailwatch_notifications",  # <— the fix
    )

    source = models.CharField(max_length=16, choices=SOURCE_CHOICES)
    external_message_id = models.CharField(max_length=255, db_index=True)
    subject = models.CharField(max_length=500)
    sender = models.CharField(max_length=255)
    snippet = models.TextField(blank=True)
    sent_at = models.DateTimeField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "external_message_id"]),
            models.Index(fields=["user", "is_read", "created_at"]),
        ]
        unique_together = ("user", "application", "external_message_id")

    def __str__(self):
        return f"{self.get_source_display()}: {self.subject[:60]}"
