# mailwatch/management/commands/seed_dummy_notification.py
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils import timezone

import uuid

# Adjust these imports / field names to match your project
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
        parser.add_argument(
            "--provider", default="gmail", help="gmail | outlook | mock"
        )
        parser.add_argument("--url", default="https://example.edu/portal/inbox/123")
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

        # Pick an application to attach to
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

        # ⚠️ Match these field names to your Notification model
        notif = Notification.objects.create(
            user=user,
            application=app,  # okay if None (general inbox)
            provider=opts["provider"],  # e.g. "gmail"
            external_id=external_id,  # or message_id if that's your field
            subject=opts["subject"],
            snippet=opts["snippet"],  # or preview/body_preview
            url=opts["url"],  # or link_url
            received_at=timezone.now(),
            unread=True,  # or is_read=False
            raw={"mock": True},  # if you have a JSONField
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Created notification #{notif.pk} for {user.email} "
                f"(app={app.pk if app else 'None'}) external_id={external_id}"
            )
        )
