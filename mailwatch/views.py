from urllib.parse import urlencode
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Notification
from django.urls import reverse

from django.http import HttpResponse
from allauth.socialaccount.views import ConnectionsView


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
    For a LOGGED-IN user, this must use the "connect" flow so allauth
    links the Google account to the existing Django user instead of
    trying to log in/sign up. This avoids the generic allauth signup page.
    """
    base = reverse("google_login")
    return redirect(f"{base}?process=connect")


@login_required
def debug_oauth_callback(request):
    """
    Debug view to see what's happening in the OAuth callback.
    """
    print("=== OAUTH CALLBACK DEBUG ===")
    print("GET params:", dict(request.GET))
    print("User:", request.user)
    print("Session:", dict(request.session))

    from allauth.socialaccount.models import SocialAccount, SocialToken

    accounts = SocialAccount.objects.filter(user=request.user, provider="google")
    tokens = SocialToken.objects.filter(
        account__user=request.user, account__provider="google"
    )

    print("SocialAccounts:", list(accounts))
    print("SocialTokens:", list(tokens))

    return HttpResponse("OAuth callback debug - check console logs")


class CustomConnectionsView(ConnectionsView):
    """Custom connections view that includes our Gmail connection status."""

    def get_context_data(self, **kwargs):
        try:
            if self.request.user.is_authenticated:
                from allauth.socialaccount.models import SocialAccount, SocialToken

                accs = list(
                    SocialAccount.objects.filter(
                        user=self.request.user, provider="google"
                    ).order_by("-id")
                )
                if len(accs) > 1:
                    keep = accs[0]
                    older = accs[1:]
                    SocialToken.objects.filter(account__in=older).delete()
                    SocialAccount.objects.filter(id__in=[a.id for a in older]).delete()
        except Exception:
            pass

        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            has_gmail_connected = (
                SocialAccount.objects.filter(
                    user=self.request.user, provider="google"
                ).exists()
                and SocialToken.objects.filter(
                    account__user=self.request.user, account__provider="google"
                ).exists()
            )
        else:
            has_gmail_connected = False

        context["has_gmail_connected"] = has_gmail_connected

        try:
            from allauth.socialaccount.models import SocialAccount

            accs_db = list(
                SocialAccount.objects.filter(user=self.request.user).order_by("-id")
            )
            seen = set()
            unique = []
            for a in accs_db:
                key = a.uid
                if key in seen:
                    continue
                seen.add(key)
                unique.append(a)
            context["accounts_dedup"] = unique
        except Exception:
            pass
        return context
