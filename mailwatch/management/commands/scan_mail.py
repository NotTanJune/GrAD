# mailwatch/management/commands/scan_mail.py
from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Tuple

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.models import SocialToken

from applications.models import Application  # adjust path if different
from mailwatch.models import Notification
from mailwatch.utils import (
    PROVIDER_GOOGLE,
    PROVIDER_MICROSOFT,
    InboxMessage,
    get_access_token,
    gmail_search_messages,
    gmail_get_message,
    graph_list_recent,
    graph_to_inbox_message,
    likely_matches,
)

log = logging.getLogger(__name__)
User = get_user_model()

ACTIVE_STATUSES = {"submitted", "interview", "waitlist", "waitlisted"}


class Command(BaseCommand):
    help = "Scan connected Gmail/Outlook inboxes for updates related to active applications and create Notification rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user", type=str, help="Only scan for this username or email"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not write to DB, just log matches",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Look back window for searches (default 30)",
        )
        parser.add_argument(
            "--max",
            type=int,
            default=10,
            help="Max messages per app/provider to fetch (Gmail)",
        )

    def handle(self, *args, **opts):
        qs = User.objects.all()
        if opts.get("user"):
            qs = qs.filter(username=opts["user"]) | qs.filter(email=opts["user"])

        users = list(qs)
        if not users:
            self.stdout.write(self.style.WARNING("No users to scan."))
            return

        total_new = 0
        for user in users:
            try:
                new_count = self.scan_user(
                    user,
                    days=opts["days"],
                    max_per_app=opts["max"],
                    dry_run=opts["dry_run"],
                )
                total_new += new_count
            except Exception as e:
                log.exception("Scan failed for user %s: %s", user, e)
                self.stderr.write(self.style.ERROR(f"Scan failed for user {user}: {e}"))
        self.stdout.write(
            self.style.SUCCESS(f"Scan complete. New notifications: {total_new}")
        )

    # ------------------------------------------------------------------------

    def scan_user(
        self, user: User, *, days: int, max_per_app: int, dry_run: bool
    ) -> int:
        # Active applications for this user
        apps = list(
            Application.objects.filter(user=user, status__in=ACTIVE_STATUSES).values(
                "id", "college_name", "program_name", "status"
            )
        )
        if not apps:
            log.info("User %s: no active applications. Skipping.", user)
            return 0

        # Build keywords per app for matching
        per_app_keywords: Dict[int, List[str]] = {}
        for a in apps:
            words = []
            if a.get("college_name"):
                words.append(a["college_name"])
            if a.get("program_name"):
                words.append(a["program_name"])
            per_app_keywords[a["id"]] = [w for w in words if w]

        # Providers connected?
        providers = set(
            SocialAccount.objects.filter(user=user).values_list("provider", flat=True)
        )
        providers &= {PROVIDER_GOOGLE, PROVIDER_MICROSOFT}
        if not providers:
            log.info("User %s: no connected Google/Microsoft accounts.", user)
            return 0

        new_count = 0
        for provider in providers:
            if provider == PROVIDER_GOOGLE:
                new_count += self._scan_gmail(
                    user, per_app_keywords, days, max_per_app, dry_run
                )
            elif provider == PROVIDER_MICROSOFT:
                new_count += self._scan_outlook(user, per_app_keywords, dry_run)
        return new_count

    # ---------------- Gmail --------------------------------------------------

    def users_with_gmail():
        # Only users who actually connected Google
        tokens = SocialToken.objects.filter(account__provider="google").select_related(
            "account__user"
        )
        seen = set()
        for t in tokens:
            u = t.account.user
            if u.pk not in seen:
                seen.add(u.pk)
                yield u

    def _scan_gmail(
        self,
        user: User,
        per_app_keywords: Dict[int, List[str]],
        days: int,
        max_per_app: int,
        dry_run: bool,
    ) -> int:
        access = get_access_token(user, PROVIDER_GOOGLE)
        created = 0

        for app_id, kws in per_app_keywords.items():
            if not kws:
                continue
            # Simple Gmail search: look back N days and search for either keyword
            # Example: newer_than:30d ("Stanford" OR "Computer Science")
            # Keep the query small and robust to quotes
            terms = " OR ".join(f'"{k.replace("\"", "")}"' for k in kws)
            q = f"newer_than:{int(days)}d ({terms})"
            try:
                ids = gmail_search_messages(access, q, max_results=max_per_app)
            except Exception as e:
                log.warning(
                    "Gmail list failed for user %s (app %s): %s", user, app_id, e
                )
                continue

            for mid in ids:
                try:
                    msg = gmail_get_message(access, mid)
                except Exception as e:
                    log.warning("Gmail get message failed: %s", e)
                    continue

                if not likely_matches(msg.subject, msg.sender, kws):
                    continue

                created += self._maybe_create_notification(
                    user=user,
                    app_id=app_id,
                    msg=msg,
                    dry_run=dry_run,
                )

        return created

    # ---------------- Outlook / Microsoft Graph -----------------------------

    def _scan_outlook(
        self,
        user: User,
        per_app_keywords: Dict[int, List[str]],
        dry_run: bool,
    ) -> int:
        access = get_access_token(user, PROVIDER_MICROSOFT)
        created = 0
        try:
            raw = graph_list_recent(access, top=30)
        except Exception as e:
            log.warning("Graph list failed for user %s: %s", user, e)
            return 0

        messages = [graph_to_inbox_message(m) for m in raw]

        for app_id, kws in per_app_keywords.items():
            if not kws:
                continue
            for msg in messages:
                if likely_matches(msg.subject, msg.sender, kws):
                    created += self._maybe_create_notification(
                        user=user, app_id=app_id, msg=msg, dry_run=dry_run
                    )
        return created

    # ---------------- Write Notification (dedup by message id) --------------

    def _maybe_create_notification(
        self, *, user: User, app_id: int, msg: InboxMessage, dry_run: bool
    ) -> int:
        # Dedup by provider message id first, then by internetMessageId (if present)
        exists = Notification.objects.filter(
            user=user,
            application_id=app_id,
            external_message_id__in=[msg.id, msg.internet_message_id or "__none__"],
        ).exists()
        if exists:
            return 0

        if dry_run:
            self.stdout.write(
                f"[DRY] {user} app#{app_id} <- {msg.provider} "
                f"{msg.sent_at:%Y-%m-%d %H:%M} | {msg.sender} | {msg.subject}"
            )
            return 0

        with transaction.atomic():
            Notification.objects.create(
                user=user,
                application_id=app_id,
                source="gmail" if msg.provider == "gmail" else "outlook",
                external_message_id=msg.internet_message_id or msg.id,
                subject=msg.subject[:500],
                sender=msg.sender[:255],
                snippet=(msg.snippet or "")[:1000],
                sent_at=msg.sent_at,
                is_read=False,
            )
        return 1
