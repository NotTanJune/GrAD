from urllib.parse import urlencode
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Notification
from django.urls import reverse


@login_required
def panel(request):
    """
    Renders the notifications card body. Loaded with HTMX from the dashboard.
    """
    items = (
        Notification.objects.filter(user=request.user)
        .order_by("-created_at")
        .select_related("application")[:15]
    )
    return render(request, "mailwatch/panel.html", {"items": items})


@login_required
def connect_gmail(request):
    """
    Redirect to allauth's Google login with 'process=connect' and the
    Gmail read-only scope + offline access so we get a refresh token.
    """
    params = {
        "process": "connect",
        "scope": "email profile https://www.googleapis.com/auth/gmail.readonly",
        "access_type": "offline",
        "prompt": "consent",
    }
    # allauth registers this name: 'google_login'
    base = reverse("google_login")
    return redirect(f"{base}?{urlencode(params)}")
