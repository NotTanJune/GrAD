from django.urls import path
from . import views

app_name = "applications"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("reorder/", views.applications_reorder, name="applications_reorder"),
    path("new/", views.application_create, name="application_create"),
    path(
        "<int:pk>/attachments/",
        views.application_attachments,
        name="application_attachments",
    ),
    path(
        "<int:pk>/status/",
        views.application_update_status,
        name="application_update_status",
    ),
    path("<int:pk>/delete/", views.delete_application, name="application_delete"),
    path("sop-assistant/", views.sop_assistant, name="sop_assistant"),
    path(
        "sop-assistant/stream/", views.sop_assistant_stream, name="sop_assistant_stream"
    ),
    path("sop-assistant/sops/", views.sop_sops_for_app, name="sop_sops_for_app"),
    path(
        "attachments/<int:pk>/download/",
        views.download_attachment,
        name="attachment_download",
    ),
    path("signup/", views.signup, name="signup"),
]
