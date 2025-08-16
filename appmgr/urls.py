from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def healthz(request):
    # Always return 200 OK with a tiny body so Fly health checks pass
    return HttpResponse("ok", status=200)


urlpatterns = [
    path("healthz", healthz, name="healthz"),  # no trailing slash
    path("healthz/", healthz),  # support trailing slash too
    path("admin/", admin.site.urls),
    path("", include("applications.urls")),
]
