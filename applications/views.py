from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
import os, boto3, io
from django.http import (
    HttpResponseForbidden,
    StreamingHttpResponse,
    HttpResponseRedirect,
    JsonResponse,
    HttpResponse,
    HttpResponseBadRequest,
)
from django.db import transaction
import json
from . import ddb
from django.views.decorators.csrf import ensure_csrf_cookie
from .ddb import put_state, get_all_states, update_status, delete_state, put_state

from django.views.decorators.http import require_POST
from .models import Application, Program, College, Document, Notification
from .forms import DocumentForm, ApplicationCreateForm
from .models import Application, Document, Notification, Attachment
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET
from groq import Groq
from .utils_s3 import read_attachment_bytes
from pdfminer.high_level import extract_text as pdf_extract
from django.contrib.auth import login as auth_login
from .forms import DocumentForm, ApplicationCreateForm, SignupForm


def home(request):
    return redirect("applications:dashboard")


@login_required
def application_attachments(request, pk: int):
    app = get_object_or_404(Application, pk=pk, user=request.user)
    return render(request, "applications/application_attachments.html", {"app": app})


@login_required
@require_POST
def delete_application(request, pk):
    is_htmx = (
        request.headers.get("HX-Request", "").lower() == "true"
        or bool(request.META.get("HTTP_HX_REQUEST"))
    )
    # Be defensive to avoid surfacing a 404 page to htmx requests.
    # If not found, return an empty response so the row can be swapped out gracefully.
    app = Application.objects.filter(pk=pk).first()
    if app is None:
        if is_htmx:
            resp = HttpResponse("")
            resp["HX-Trigger"] = "renumber-priorities"
            return resp
        messages.info(request, "Application already deleted.")
        return redirect("applications:dashboard")

    if app.user_id != request.user.id:
        if is_htmx:
            return HttpResponseForbidden("Not allowed")
        messages.error(request, "You are not allowed to delete that application.")
        return redirect("applications:dashboard")

    # Delete any S3 files for attachments
    aws_region = os.getenv("AWS_S3_REGION_NAME", "ap-southeast-1")
    bucket = os.getenv("AWS_STORAGE_BUCKET_NAME")
    if bucket:
        s3 = boto3.client(
            "s3",
            region_name=aws_region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        keys = [
            {"Key": att.file.name}
            for att in app.attachments.all()
            if att.file and att.file.name
        ]
        if keys:
            for i in range(0, len(keys), 1000):
                s3.delete_objects(Bucket=bucket, Delete={"Objects": keys[i : i + 1000]})

    username = request.user.username
    app.delete()

    remaining = list(
        Application.objects.filter(user=request.user)
        .order_by("priority", "-last_updated", "id")
        .only("id", "priority")
    )
    for idx, a in enumerate(remaining, start=1):
        if a.priority != idx:
            Application.objects.filter(id=a.id, user=request.user).update(priority=idx)
        try:
            from . import ddb as _ddb

            _ddb.update_priority(username, a.id, idx)
        except Exception:
            pass

    if is_htmx:
        resp = HttpResponse("")
        resp["HX-Trigger"] = "renumber-priorities"
        return resp
    messages.success(request, "Application deleted.")
    return redirect("applications:dashboard")


@login_required
def download_attachment(request, pk):
    att = get_object_or_404(Attachment, pk=pk)
    if att.application.user_id != request.user.id:
        return HttpResponseForbidden("Not allowed")

    s3 = boto3.client(
        "s3",
        region_name=os.getenv("AWS_S3_REGION_NAME", "ap-southeast-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    bucket = os.getenv("AWS_STORAGE_BUCKET_NAME")
    presigned = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": att.file.name},
        ExpiresIn=300,
    )
    return HttpResponseRedirect(presigned)


@require_POST
@login_required
def applications_reorder(request):
    try:
        payload = json.loads(request.body or "{}")
        order = [int(x) for x in payload.get("order", [])]
    except Exception:
        return HttpResponseBadRequest("Bad JSON")

    apps = Application.objects.filter(user=request.user, id__in=order).only(
        "id", "status"
    )
    allowed = {a.id: a for a in apps}
    sequence = [aid for aid in order if aid in allowed]

    with transaction.atomic():
        for idx, app_id in enumerate(sequence, start=1):
            Application.objects.filter(id=app_id, user=request.user).update(
                priority=idx, last_updated=timezone.now()
            )
            ddb.update_priority(request.user.username, app_id, priority=idx)

    return JsonResponse({"ok": True, "order": sequence})


@login_required
@ensure_csrf_cookie
def dashboard(request):
    apps = list(
        Application.objects.filter(user=request.user).order_by(
            "priority", "-last_updated", "id"
        )
    )

    states = get_all_states(request.user.username)
    for a in apps:
        st = states.get(str(a.id))
        if st and "status" in st:
            a.status = st["status"]

    status_choices = Application._meta.get_field("status").choices
    notifs = Notification.objects.order_by("-received_at")[:10]
    return render(
        request,
        "applications/dashboard.html",
        {
            "apps": apps,
            "notifs": notifs,
            "status_choices": status_choices,
        },
    )


@login_required
def application_create(request):
    app = None
    if request.method == "POST":
        form = ApplicationCreateForm(request.POST)
        if form.is_valid():
            app = form.save(commit=False)
            app.user = request.user
            app.status = "draft"
            next_priority = Application.objects.filter(user=request.user).count() + 1
            app.priority = next_priority
            app.save()
            app.status = "submitted"
            app.save(update_fields=["status"])

            put_state(
                request.user.username,
                app.id,
                app.status,
                getattr(app, "priority", next_priority),
            )

            messages.success(
                request,
                "Application created. Upload your SOP/LOR/Other documents below.",
            )
        else:
            messages.error(request, "Please fix the errors and try again.")
    else:
        form = ApplicationCreateForm()

    return render(
        request, "applications/application_form.html", {"form": form, "app": app}
    )


@login_required
def application_update_status(request, pk):
    app = get_object_or_404(Application, pk=pk, user=request.user)
    if request.method == "POST":
        new_status = request.POST.get("status")
        valid = dict(Application._meta.get_field("status").choices)
        if new_status in valid:
            app.status = new_status
            update_status(
                request.user.username,
                app.id,
                new_status,
                priority=getattr(app, "priority", 999),
            )
    status_choices = Application._meta.get_field("status").choices
    return render(
        request,
        "applications/partials/app_row.html",
        {
            "app": app,
            "status_choices": status_choices,
        },
    )


@login_required
def documents(request):
    docs = Document.objects.order_by("-updated_at")
    if request.method == "POST":
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Document saved.")
            return redirect("applications:documents")
    else:
        form = DocumentForm()
    return render(request, "applications/documents.html", {"docs": docs, "form": form})


@login_required
def sop_assistant(request):
    outline = None
    if request.method == "POST":
        profile = request.POST.get("profile", "")
        program = request.POST.get("program", "")
        constraints = request.POST.get("constraints", "")
        outline = generate_sop_outline(profile, program, constraints)
    return render(request, "applications/sop_assistant.html", {"outline": outline})


def extract_text_from_bytes(filename, data: bytes) -> str:
    name = (filename or "").lower()
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")
    if name.endswith(".docx"):
        from docx import Document as Docx

        d = Docx(io.BytesIO(data))
        return "\n".join(p.text for p in d.paragraphs)
    if name.endswith(".pdf"):
        return pdf_extract(io.BytesIO(data))
    return data.decode("utf-8", errors="ignore")


def fetch_sop_expectations(college: str, program: str) -> str:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return ""
    try:
        from tavily import TavilyClient

        tv = TavilyClient(api_key=api_key)
        q = f"what do admissions committees at {college} look for in a Statement of Purpose for {program}? key components, common pitfalls, recommended structure"
        res = tv.search(q, max_results=5)
        bullets = []
        for item in res.get("results", [])[:5]:
            title = item.get("title", "")
            content = item.get("content", "")
            bullets.append(f"- {title}: {content[:300]}...")
        return "Web research highlights:\n" + "\n".join(bullets)
    except Exception:
        return ""


def groq_stream_markdown(sop_text: str, college: str, program: str, notes: str):
    """
    Stream **markdown** chunks from Groq. We instruct the model to output
    only markdown with specific section headings.
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    model = os.getenv("GROQ_STREAM_MODEL", "openai/gpt-oss-20b")

    system = (
        "You are an admissions editor. Use the browser_search tool if helpful to check "
        "expectations for a strong SOP for the given college/program. "
        "Output MARKDOWN ONLY with these sections:\n"
        "# Executive Summary\n"
        "## Overall Score (0–10)\n"
        "## Category Ratings\n"
        "## Program Fit (College/Faculty/Research Alignment)\n"
        "## Strengths\n"
        "## Issues / Gaps\n"
        "## High-Impact Edits (bullet list)\n"
        "Keep it concise, concrete, skimmable. No prose outside markdown."
    )
    user = (
        f"College: {college}\nProgram: {program}\nEvaluator notes: {notes or '(none)'}\n\n"
        "Do a brief browser_search if needed, then analyze this SOP:\n"
        f"---BEGIN SOP---\n{sop_text[:70000]}\n---END SOP---"
    )

    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        top_p=1,
        max_completion_tokens=4096,
        reasoning_effort="medium",
        tools=[{"type": "browser_search"}],
        stream=True,
    )

    for chunk in stream:
        yield (chunk.choices[0].delta.content or "").encode("utf-8")


@login_required
def sop_assistant(request):
    """
    Renders the page with selectors and a 'Stream analysis' button.
    No POST handler: analysis is done via GET /stream/.
    """
    apps = Application.objects.filter(user=request.user).order_by(
        "priority", "-last_updated"
    )
    return render(request, "applications/sop_assistant.html", {"apps": apps})


@login_required
def sop_assistant_stream(request):
    """
    Streams markdown. Query params:
      ?application_id=<id>&attachment_id=<id>&notes=<text>
    """
    app_id = (request.GET.get("application_id") or "").strip()
    att_id = (request.GET.get("attachment_id") or "").strip()
    notes = (request.GET.get("notes") or "").strip()
    if not (app_id.isdigit() and att_id.isdigit()):
        return HttpResponseBadRequest("Pick an application and an SOP.")

    att = get_object_or_404(
        Attachment,
        pk=int(att_id),
        application__user=request.user,
        application_id=int(app_id),
        doc_type="SOP",
    )
    app = att.application

    data = read_attachment_bytes(att)  # S3-safe
    text = extract_text_from_bytes(att.title or att.file.name, data).strip()
    if not text:
        return HttpResponseBadRequest("Could not extract text from that file.")

    resp = StreamingHttpResponse(
        groq_stream_markdown(text, app.college_name, app.program_name, notes),
        content_type="text/plain; charset=utf-8",
    )
    resp["Cache-Control"] = "no-cache"
    return resp


@login_required
@require_GET
def sop_sops_for_app(request):
    app_id = str(request.GET.get("application_id", "")).strip()
    if not app_id.isdigit():
        html = '<label class="text-sm block mb-1">SOP file</label><select name="attachment_id" class="w-full border rounded p-2"><option value="">-- Select SOP --</option></select>'
        return HttpResponse(html)
    sops = Attachment.objects.filter(
        application__user=request.user, application_id=int(app_id), doc_type="SOP"
    ).order_by("-created_at")
    html = render_to_string(
        "applications/partials/_sop_select.html", {"sops": sops}, request=request
    )
    return HttpResponse(html)


def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect("applications:dashboard")
    else:
        form = SignupForm()
    return render(request, "registration/signup.html", {"form": form})
