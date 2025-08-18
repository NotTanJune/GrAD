from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.conf import settings


class Command(BaseCommand):
    help = "Set up OAuth SocialApp records for Google and Microsoft"

    def add_arguments(self, parser):
        parser.add_argument(
            "--google-client-id",
            type=str,
            help="Google OAuth Client ID",
        )
        parser.add_argument(
            "--google-client-secret",
            type=str,
            help="Google OAuth Client Secret",
        )
        parser.add_argument(
            "--microsoft-client-id",
            type=str,
            help="Microsoft OAuth Client ID",
        )
        parser.add_argument(
            "--microsoft-client-secret",
            type=str,
            help="Microsoft OAuth Client Secret",
        )

    def handle(self, *args, **options):
        site = Site.objects.get(id=settings.SITE_ID)

        # Set up Google OAuth
        if options.get("google_client_id") and options.get("google_client_secret"):
            google_app, created = SocialApp.objects.get_or_create(
                provider="google",
                defaults={
                    "name": "Google OAuth",
                    "client_id": options["google_client_id"],
                    "secret": options["google_client_secret"],
                },
            )
            if not created:
                google_app.client_id = options["google_client_id"]
                google_app.secret = options["google_client_secret"]
                google_app.save()

            google_app.sites.add(site)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Google OAuth app {'created' if created else 'updated'}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING("Google OAuth credentials not provided, skipping...")
            )

        # Set up Microsoft OAuth
        if options.get("microsoft_client_id") and options.get(
            "microsoft_client_secret"
        ):
            microsoft_app, created = SocialApp.objects.get_or_create(
                provider="microsoft",
                defaults={
                    "name": "Microsoft OAuth",
                    "client_id": options["microsoft_client_id"],
                    "secret": options["microsoft_client_secret"],
                },
            )
            if not created:
                microsoft_app.client_id = options["microsoft_client_id"]
                microsoft_app.secret = options["microsoft_client_secret"]
                microsoft_app.save()

            microsoft_app.sites.add(site)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Microsoft OAuth app {'created' if created else 'updated'}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Microsoft OAuth credentials not provided, skipping..."
                )
            )
