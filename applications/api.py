import os, datetime, json, urllib.parse
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
import boto3

from .models import Application, Attachment


@login_required
@require_GET
def create_presigned_post(request):
    app_id_raw = request.GET.get("application_id", "")
    try:
        app_id = int(str(app_id_raw).strip())
    except ValueError:
        return HttpResponseBadRequest("bad application_id")
    filename = request.GET.get("filename")
    doc_type = request.GET.get("doc_type")  # SOP or LOR
    if not (app_id and filename and doc_type in ("SOP", "LOR", "RESUME", "OTHER")):
        return HttpResponseBadRequest("missing params or bad doc_type")

    app = Application.objects.get(pk=app_id, user=request.user)

    user_part = request.user.username.replace("/", "-")
    college_part = app.college_name.replace("/", "-")
    program_part = app.program_name.replace("/", "-")
    safe_name = os.path.basename(filename)
    prefix = f"{user_part}/{college_part}/{program_part}/{doc_type}"
    key = f"{prefix}/{int(datetime.datetime.utcnow().timestamp())}_{safe_name}"

    s3 = boto3.client(
        "s3",
        region_name=os.getenv("AWS_S3_REGION_NAME", "ap-southeast-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    bucket = os.getenv("AWS_STORAGE_BUCKET_NAME")
    fields = {
        "acl": "private",
        "Content-Type": request.GET.get("content_type", "application/octet-stream"),
    }
    conditions = [
        {"acl": "private"},
        ["starts-with", "$Content-Type", ""],
        ["content-length-range", 0, 25 * 1024 * 1024],
    ]
    resp = s3.generate_presigned_post(
        Bucket=bucket, Key=key, Fields=fields, Conditions=conditions, ExpiresIn=300
    )
    return JsonResponse({"post": resp, "key": key})


@login_required
@require_POST
def finalize_upload(request):
    import json

    try:
        data = json.loads(request.body.decode())
        app_id = int(str(data["application_id"]).strip())
        doc_type = data["doc_type"]
        title = (data.get("title") or "").strip() or "Untitled"
        key = data["key"]
    except Exception:
        return HttpResponseBadRequest("bad payload")

    app = Application.objects.get(pk=app_id, user=request.user)
    att = Attachment(application=app, doc_type=doc_type, title=title)
    att.file.name = key
    att.save()
    return JsonResponse({"id": att.id, "title": att.title})
