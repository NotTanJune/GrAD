# mailwatch/urls.py
from django.urls import path
from . import views

app_name = "mailwatch"  # <- gives us the 'mailwatch:' namespace

urlpatterns = [
    path("panel/", views.panel, name="panel"),
    path("connect/google/", views.connect_gmail, name="connect_gmail"),
]
