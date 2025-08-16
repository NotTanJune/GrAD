from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path, include
from applications import views as app_views
from django.views.generic import RedirectView


def healthz(request):
    return HttpResponse("ok", status=200, content_type="text/plain")


# urlpatterns = [
#     path("healthz", healthz, name="healthz"),
#     path("accounts/", include("django.contrib.auth.urls")),
#     path("admin/", admin.site.urls),
#     path("", include("applications.urls")),
# ]

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "", RedirectView.as_view(pattern_name="applications:dashboard", permanent=False)
    ),
    path("applications/", include("applications.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/signup/", app_views.signup, name="signup"),
    path("api/", include("applications.api_urls")),
    path("healthz", healthz, name="healthz"),
]
