from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from applications import views as app_views
from appmgr.health import healthz


urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "", RedirectView.as_view(pattern_name="applications:dashboard", permanent=False)
    ),
    path("applications/", include("applications.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/signup/", app_views.signup, name="signup"),
    path("api/", include("applications.api_urls")),
    path("healthz", healthz),
]
