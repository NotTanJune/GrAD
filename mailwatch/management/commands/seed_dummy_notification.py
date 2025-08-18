"""Seed a dummy Mailwatch Notification conforming to current model fields."""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone

import uuid

from applications.models import Application
from mailwatch.models import Notification

ACTIVE_STATUSES = [
    "submitted",
    "interview",
    "waitlist",
    "waitlisted",
    "review",
    "under_review",
]


class Command(BaseCommand):
    help = "Create a fake email notification for UI testing (no Gmail needed)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email", required=True, help="User email to attach the notification to."
        )
        parser.add_argument("--subject", default="[Portal] Application update")
        parser.add_argument(
            "--snippet",
            default="We have received your documents and will update you soon.",
        )
        parser.add_argument("--source", default="gmail", help="gmail | outlook | mock")
        parser.add_argument(
            "--sender",
            default="admissions@example.edu",
            help="Sender display/email to show in UI",
        )
        parser.add_argument(
            "--app-id", type=int, help="Optional: specific Application.pk to link."
        )
        parser.add_argument(
            "--status", default=None, help="Optional: filter apps by this status first."
        )

    def handle(self, *args, **opts):
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=opts["email"])
        except User.DoesNotExist:
            raise CommandError(f"No user found with email {opts['email']}")
        app = None
        if opts["app_id"]:
            app = Application.objects.filter(pk=opts["app_id"], user=user).first()
            if not app:
                raise CommandError(
                    f"Application {opts['app_id']} not found for {user.email}"
                )
        else:
            status_filter = [opts["status"]] if opts["status"] else ACTIVE_STATUSES
            app = (
                Application.objects.filter(user=user, status__in=status_filter)
                .order_by("priority", "-last_updated")
                .first()
            )

        external_id = f"dummy-{uuid.uuid4().hex[:12]}"

        notif = Notification.objects.create(
            user=user,
            application=app,
            source=opts["source"],
            external_message_id=external_id,
            subject=opts["subject"],
            sender=opts["sender"],
            snippet=opts["snippet"],
            sent_at=timezone.now(),
            is_read=False,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created notification #{notif.pk} for {user.email} "
                f"(app={app.pk if app else 'None'}) external_message_id={external_id}"
            )
        )
