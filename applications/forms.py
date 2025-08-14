from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import Application, Document

User = get_user_model()


class SignupForm(UserCreationForm):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "w-full rounded-xl border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm p-2.5 focus:outline-none focus:ring-2 focus:ring-brand-500 transition",
                "autocomplete": "username",
                "placeholder": "your username",
            }
        ),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": "w-full rounded-xl border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm p-2.5 focus:outline-none focus:ring-2 focus:ring-brand-500 transition",
                "autocomplete": "email",
                "placeholder": "you@example.com",
            }
        ),
    )
    password1 = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full pr-10 rounded-xl border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm p-2.5 focus:outline-none focus:ring-2 focus:ring-brand-500 transition",
                "autocomplete": "new-password",
                "placeholder": "",
            }
        ),
    )
    password2 = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full pr-10 rounded-xl border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm p-2.5 focus:outline-none focus:ring-2 focus:ring-brand-500 transition",
                "autocomplete": "new-password",
                "placeholder": "",
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            raise forms.ValidationError("Email is required")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists")
        return email


class ApplicationCreateForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["college_name", "program_name", "portal_url", "notes"]
        base_classes = "w-full rounded-xl border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm p-2.5 focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
        widgets = {
            "college_name": forms.TextInput(attrs={"class": base_classes}),
            "program_name": forms.TextInput(attrs={"class": base_classes}),
            "portal_url": forms.URLInput(attrs={"class": base_classes}),
            "notes": forms.Textarea(attrs={"class": base_classes + " ", "rows": 4}),
        }


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["doc_type", "title", "content", "file"]
