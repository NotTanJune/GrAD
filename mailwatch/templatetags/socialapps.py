# mailwatch/templatetags/socialapps.py
from django import template
from django.contrib.sites.shortcuts import get_current_site
from allauth.socialaccount.models import SocialApp

register = template.Library()


@register.simple_tag(takes_context=True)
def enabled_providers(context):
    request = context.get("request")
    if not request:
        return set()
    site = get_current_site(request)
    return set(SocialApp.objects.filter(sites=site).values_list("provider", flat=True))
