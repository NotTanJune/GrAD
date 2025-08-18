from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from django.conf import settings


class Command(BaseCommand):
    help = "Set up the Site record for django-allauth"

    def handle(self, *args, **options):
        try:
            site = Site.objects.get(id=settings.SITE_ID)
            site.domain = "grad-app.fly.dev"
            site.name = "Grab a Degree"
            site.save()
            self.stdout.write(self.style.SUCCESS(f"Updated existing site: {site}"))
        except Site.DoesNotExist:
            site = Site.objects.create(
                id=settings.SITE_ID, domain="grad-app.fly.dev", name="Grab a Degree"
            )
            self.stdout.write(self.style.SUCCESS(f"Created new site: {site}"))
