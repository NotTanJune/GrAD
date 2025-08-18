from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import Application, Document

User = get_user_model()


class SignupForm(UserCreationForm):
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
        fields = ("email", "password1", "password2")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Email is required")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists")
        return email

    def _generate_username(self, email: str) -> str:
        base = email.split("@")[0][:20] or "user"
        candidate = base
        suffix = 1
        while User.objects.filter(username__iexact=candidate).exists():
            suffix += 1
            candidate = f"{base}{suffix}"
        return candidate

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data.get("email", "")
        user.email = email
        if not getattr(user, "username", ""):
            user.username = self._generate_username(email)
        if commit:
            user.save()
        return user


class ApplicationCreateForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["college_name", "program_name", "portal_url", "notes"]
        base_classes = "w-full rounded-xl border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 text-sm p-2.5 focus:outline-none focus:ring-2 focus:ring-brand-500 transition"
        widgets = {
            "college_name": forms.TextInput(attrs={"class": base_classes}),
            "program_name": forms.TextInput(attrs={"class": base_classes}),
            "portal_url": forms.URLInput(attrs={"class": base_classes}),
            "notes": forms.Textarea(attrs={"class": base_classes + " ", "rows": 3}),
        }


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["doc_type", "title", "content", "file"]
