from django.urls import path
from . import api

urlpatterns = [
    path("presign/", api.create_presigned_post, name="api_presign"),
    path("finalize/", api.finalize_upload, name="api_finalize"),
]
