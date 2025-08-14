import os, email, imaplib, datetime
from email.header import decode_header, make_header
from django.core.management.base import BaseCommand
from django.utils import timezone
from applications.models import Notification


class Command(BaseCommand):
    help = "Scan IMAP inbox for university notifications and store them."

    def handle(self, *args, **opts):
        host = os.getenv("APPMGR_IMAP_HOST")
        user = os.getenv("APPMGR_IMAP_USER")
        pwd = os.getenv("APPMGR_IMAP_PASS")
        if not all([host, user, pwd]):
            self.stdout.write(
                self.style.WARNING("Set APPMGR_IMAP_HOST/USER/PASS env vars.")
            )
            return

        M = imaplib.IMAP4_SSL(host)
        M.login(user, pwd)
        for mailbox in ["INBOX", "Junk", "Spam"]:
            try:
                M.select(mailbox)
            except Exception:
                continue
            status, data = M.search(None, "UNSEEN")
            if status != "OK":
                continue
            for num in data[0].split():
                status, msgdata = M.fetch(num, "(RFC822)")
                if status != "OK":
                    continue
                msg = email.message_from_bytes(msgdata[0][1])
                subject = str(make_header(decode_header(msg.get("Subject", ""))))
                date_hdr = msg.get("Date")
                try:
                    received_at = datetime.datetime.fromtimestamp(
                        email.utils.mktime_tz(email.utils.parsedate_tz(date_hdr)),
                        tz=timezone.utc,
                    )
                except Exception:
                    received_at = timezone.now()

                # Extract a short text snippet
                snippet = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            snippet = part.get_payload(decode=True).decode(
                                errors="ignore"
                            )[:500]
                            break
                else:
                    if msg.get_content_type() == "text/plain":
                        snippet = msg.get_payload(decode=True).decode(errors="ignore")[
                            :500
                        ]

                Notification.objects.create(
                    source=mailbox,
                    subject=subject or "(no subject)",
                    snippet=snippet or "",
                    received_at=received_at,
                )
                self.stdout.write(self.style.SUCCESS(f"Ingested: {subject[:60]}"))
        M.logout()
