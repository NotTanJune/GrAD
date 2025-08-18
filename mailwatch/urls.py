# mailwatch/urls.py
from django.urls import path
from . import views

app_name = "mailwatch"

urlpatterns = [
    path("panel/", views.panel, name="panel"),
    path("connect/google/", views.connect_gmail, name="connect_gmail"),
    path("connections/", views.CustomConnectionsView.as_view(), name="connections"),
    path("debug/oauth/", views.debug_oauth_callback, name="debug_oauth"),
]
