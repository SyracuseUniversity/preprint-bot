"""
Django forms for authentication, profile CRUD, and paper uploads.
"""

from django import forms
from .models import Profile


# ── Auth ───────────────────────────────────────────────────────────────────

class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com", "autofocus": True}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••"}),
    )


class RegisterForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com", "autofocus": True}),
    )
    name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Your name (optional)"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Choose a password"}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm password"}),
    )

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        confirm = cleaned.get("confirm_password")
        if pw and confirm and pw != confirm:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "you@example.com"}),
    )


class ResetPasswordForm(forms.Form):
    token = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Paste your reset token"}),
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "New password"}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Confirm new password"}),
    )

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("new_password")
        confirm = cleaned.get("confirm_password")
        if pw and confirm and pw != confirm:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned


# ── Profiles ───────────────────────────────────────────────────────────────

FREQUENCY_CHOICES = [
    ("daily", "Daily"),
    ("weekly", "Weekly"),
    ("monthly", "Monthly"),
]


class ProfileForm(forms.Form):
    """Create / edit a research profile."""

    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "e.g. AI Research"}),
    )
    frequency = forms.ChoiceField(choices=FREQUENCY_CHOICES, initial="weekly")
    threshold = forms.FloatField(
        min_value=0.40,
        max_value=0.75,
        initial=0.575,
        widget=forms.HiddenInput(),  # actual input is the range slider in the template
        help_text="Lower = more results, higher = stricter matching.",
    )
    top_x = forms.IntegerField(
        min_value=5,
        max_value=999,
        initial=999,
        label="Max recommendations",
        help_text="Set to 999 for unlimited.",
    )
    keywords = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "machine learning, transformers, ..."}),
        help_text="Comma-separated.",
    )
    categories = forms.CharField(
        widget=forms.HiddenInput(),
        required=True,
        help_text="Selected via the category tree widget (stored as comma-separated codes).",
    )

    def clean_keywords(self):
        raw = self.cleaned_data.get("keywords", "")
        return [kw.strip() for kw in raw.split(",") if kw.strip()]

    def clean_categories(self):
        raw = self.cleaned_data.get("categories", "")
        cats = [c.strip() for c in raw.split(",") if c.strip()]
        if not cats:
            raise forms.ValidationError("Select at least one arXiv category.")
        return cats


# ── Paper upload ───────────────────────────────────────────────────────────

class PaperUploadForm(forms.Form):
    # The profile list template uses a raw <input type="file" multiple> instead
    # of rendering this form, so we keep it minimal.
    files = forms.FileField(required=False)


class ArxivIdForm(forms.Form):
    arxiv_ids = forms.CharField(
        widget=forms.Textarea(attrs={
            "rows": 3,
            "placeholder": "2301.12345, 2302.67890\nor one per line",
        }),
    )


# ── Settings ───────────────────────────────────────────────────────────────

class UserSettingsForm(forms.Form):
    name = forms.CharField(required=False, widget=forms.TextInput(attrs={"placeholder": "Your name"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "you@example.com"}))
