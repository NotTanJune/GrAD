from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Notification


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
