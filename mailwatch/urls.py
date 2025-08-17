from django.urls import path
from . import views

app_name = "mailwatch"

urlpatterns = [
    path("panel/", views.panel, name="panel"),
]
