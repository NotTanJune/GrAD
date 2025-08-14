from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


class College(models.Model):
    name = models.CharField(max_length=255)
    website = models.URLField(blank=True)
    country = models.CharField(max_length=128, blank=True)

    def __str__(self):
        return self.name


class Program(models.Model):
    DEGREE_CHOICES = [
        ("UG", "Undergraduate"),
        ("PG", "Postgraduate"),
    ]
    college = models.ForeignKey(
        College, on_delete=models.CASCADE, related_name="programs"
    )
    degree = models.CharField(max_length=2, choices=DEGREE_CHOICES, default="PG")
    title = models.CharField(max_length=255)
    deadline = models.DateTimeField(null=True, blank=True)
    priority = models.PositiveIntegerField(default=3, help_text="1=highest priority")

    def __str__(self):
        return f"{self.college.name} – {self.title}"


class Recommender(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=64, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Document(models.Model):
    DOC_TYPES = [
        ("SOP", "Statement of Purpose"),
        ("LOR", "Letter of Recommendation"),
        ("RESUME", "Resume/CV"),
        ("OTHER", "Other"),
    ]
    application = models.ForeignKey(
        "Application", on_delete=models.CASCADE, related_name="documents"
    )
    doc_type = models.CharField(max_length=10, choices=DOC_TYPES)
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)  # store markdown/plain text
    file = models.FileField(upload_to="docs/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_doc_type_display()}: {self.title}"


class Application(models.Model):
    college_name = models.CharField(max_length=255, default="", blank=True)
    program_name = models.CharField(max_length=255, default="", blank=True)
    priority = models.PositiveIntegerField(default=1)
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("interview", "Interview"),
        ("offer", "Offer"),
        ("rejected", "Rejected"),
        ("waitlist", "Waitlist"),
    ]
    program = models.ForeignKey(
        Program,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="draft")
    sop = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sop_for",
    )
    lors = models.ManyToManyField(Document, blank=True, related_name="lors_for")
    portal_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} -> {self.program}"


class Notification(models.Model):
    source = models.CharField(max_length=128, default="email")
    subject = models.CharField(max_length=512)
    snippet = models.TextField(blank=True)
    received_at = models.DateTimeField()
    is_unread = models.BooleanField(default=True)
    related_application = models.ForeignKey(
        Application, null=True, blank=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return f"{self.received_at:%Y-%m-%d} | {self.subject[:60]}"


# comment
class Attachment(models.Model):
    DOC_TYPES = [
        ("SOP", "Statement of Purpose"),
        ("LOR", "Letter of Recommendation"),
    ]
    application = models.ForeignKey(
        "Application", on_delete=models.CASCADE, related_name="attachments"
    )
    doc_type = models.CharField(max_length=10, choices=DOC_TYPES)
    title = models.CharField(max_length=255)
    file = models.FileField(
        upload_to="docs/"
    )  # path will actually be S3; key set by us
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.doc_type}: {self.title}"
