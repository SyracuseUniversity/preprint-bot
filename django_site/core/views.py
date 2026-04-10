"""
Django views for the Preprint Bot web interface.

All views that require login check for a PBUser stored on the Django session
(not Django's built-in auth.User).
"""

import json
import re
import shutil
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from django.conf import settings as django_settings
from django.contrib import messages
from django.db.models import Max, Subquery, OuterRef
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .arxiv_categories import ARXIV_CODE_TO_LABEL, ARXIV_CATEGORY_TREE, label_for
from .auth_backend import (
    authenticate_pbuser,
    get_current_pbuser,
    hash_password,
    login_pbuser,
    logout_pbuser,
    verify_password,
)
from .forms import (
    ArxivIdForm,
    ForgotPasswordForm,
    LoginForm,
    PaperUploadForm,
    ProfileForm,
    RegisterForm,
    ResetPasswordForm,
    UserSettingsForm,
)
from .models import (
    Corpus,
    PBUser,
    Paper,
    Profile,
    ProfileRecommendation,
    Recommendation,
    RecommendationRun,
    Summary,
)

ARXIV_ID_RE = re.compile(
    r"^(\d{4}\.\d{4,5}|[a-z-]+(?:\.[a-z-]+)?/\d{7})$", re.IGNORECASE
)


# ── Decorator ──────────────────────────────────────────────────────────────

def pbuser_required(view_func):
    """Redirect to login if no PBUser is on the session, preserving the
    originally requested URL so we can bounce back after sign-in."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        pb_user = get_current_pbuser(request)
        if pb_user is None:
            from django.utils.http import urlencode

            login_url = "/auth/login/"
            # Preserve the page the user was trying to reach
            next_url = request.get_full_path()
            return redirect(f"{login_url}?{urlencode({'next': next_url})}")
        request.pb_user = pb_user
        return view_func(request, *args, **kwargs)

    return wrapper


# ── Auth views ─────────────────────────────────────────────────────────────

def login_view(request):
    if get_current_pbuser(request):
        return redirect("dashboard")

    next_url = request.GET.get("next", request.POST.get("next", ""))

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        pb_user = authenticate_pbuser(request, email, password)
        if pb_user:
            login_pbuser(request, pb_user)
            # Redirect to the page the user originally requested, or dashboard
            return redirect(next_url if next_url else "dashboard")
        messages.error(request, "Invalid email or password.")

    return render(request, "auth/login.html", {"form": form, "next": next_url})


def register_view(request):
    if get_current_pbuser(request):
        return redirect("dashboard")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        name = form.cleaned_data.get("name", "")
        password = form.cleaned_data["password"]

        if PBUser.objects.filter(email__iexact=email).exists():
            messages.error(request, "An account with that email already exists.")
        else:
            pb_user = PBUser.objects.create(
                email=email,
                name=name,
                password_hash=hash_password(password),
            )
            login_pbuser(request, pb_user)
            messages.success(request, "Account created successfully!")
            return redirect("dashboard")

    return render(request, "auth/register.html", {"form": form})


def logout_view(request):
    logout_pbuser(request)
    return redirect("login")


def forgot_password_view(request):
    form = ForgotPasswordForm(request.POST or None)
    token_display = None
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        try:
            pb_user = PBUser.objects.get(email__iexact=email)
            import secrets

            token = secrets.token_urlsafe(32)
            from .models import PasswordReset

            PasswordReset.objects.create(
                user=pb_user,
                token=token,
                expires_at=timezone.now() + timedelta(hours=1),
            )
            # In production, send via email. For dev, display it.
            token_display = token
            messages.success(request, "If that email exists, a reset token has been generated.")
        except PBUser.DoesNotExist:
            messages.success(request, "If that email exists, a reset token has been generated.")

    return render(
        request, "auth/forgot_password.html", {"form": form, "token_display": token_display}
    )


def reset_password_view(request):
    form = ResetPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        from .models import PasswordReset

        token = form.cleaned_data["token"]
        new_password = form.cleaned_data["new_password"]
        try:
            pr = PasswordReset.objects.get(token=token, used_at__isnull=True)
            if pr.expires_at < timezone.now():
                messages.error(request, "Token has expired.")
            else:
                pr.user.password_hash = hash_password(new_password)
                pr.user.save()
                pr.used_at = timezone.now()
                pr.save()
                messages.success(request, "Password updated. Please log in.")
                return redirect("login")
        except PasswordReset.DoesNotExist:
            messages.error(request, "Invalid or already-used token.")

    return render(request, "auth/reset_password.html", {"form": form})


# ── Dashboard ──────────────────────────────────────────────────────────────

@pbuser_required
def dashboard_view(request):
    pb_user = request.pb_user

    profiles = Profile.objects.filter(user=pb_user)
    corpora = Corpus.objects.filter(user=pb_user)

    # Gather today's recommendations across all profiles
    today_recs = _get_latest_recommendations(pb_user)

    return render(
        request,
        "dashboard.html",
        {
            "pb_user": pb_user,
            "profiles": profiles,
            "corpora": corpora,
            "today_recs": today_recs[:20],
            "today_count": len(today_recs),
        },
    )


def _get_latest_recommendations(pb_user):
    """Return deduplicated recommendations from the most recent date."""
    profiles = Profile.objects.filter(user=pb_user)
    if not profiles.exists():
        return []

    # Get all profile recommendations for this user
    pr_qs = ProfileRecommendation.objects.filter(
        profile__in=profiles
    ).select_related("recommendation__paper", "recommendation__run")

    if not pr_qs.exists():
        return []

    # Find the most recent submitted_date
    recs_with_dates = []
    for pr in pr_qs:
        rec = pr.recommendation
        paper = rec.paper
        if paper.submitted_date:
            recs_with_dates.append((paper.submitted_date.date(), rec, paper))

    if not recs_with_dates:
        return []

    most_recent = max(d for d, _, _ in recs_with_dates)

    # Filter to that date, deduplicate by arxiv_id keeping highest score
    seen = {}
    for dt, rec, paper in recs_with_dates:
        if dt != most_recent:
            continue
        aid = paper.arxiv_id or f"_pk_{paper.pk}"
        if aid not in seen or rec.score > seen[aid]["score"]:
            # Try to get summary
            summary_text = ""
            try:
                s = Summary.objects.filter(paper=paper).first()
                if s:
                    summary_text = s.summary_text or ""
            except Exception:
                pass

            seen[aid] = {
                "title": paper.title,
                "score": rec.score,
                "arxiv_id": paper.arxiv_id,
                "abstract": paper.abstract or "",
                "summary_text": summary_text,
                "submitted_date": paper.submitted_date,
            }

    results = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
    return results


# ── Profiles ───────────────────────────────────────────────────────────────

@pbuser_required
def profile_list_view(request):
    pb_user = request.pb_user
    profiles = Profile.objects.filter(user=pb_user).order_by("-created_at")

    # Gather paper counts per profile
    profile_data = []
    for profile in profiles:
        corpus_name = f"user_{pb_user.pk}_profile_{profile.pk}"
        paper_count = 0
        try:
            corpus = Corpus.objects.get(user=pb_user, name=corpus_name)
            paper_count = Paper.objects.filter(corpus=corpus).count()
        except Corpus.DoesNotExist:
            pass

        # Count uploaded PDFs on disk
        pdf_dir = django_settings.USER_PDF_DIR / str(pb_user.pk) / str(profile.pk)
        pdf_files = list(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []

        profile_data.append({
            "profile": profile,
            "paper_count": paper_count,
            "pdf_files": pdf_files,
            "categories_display": [label_for(c) for c in (profile.categories or [])],
        })

    return render(request, "profiles/list.html", {
        "pb_user": pb_user,
        "profile_data": profile_data,
        "code_to_label": ARXIV_CODE_TO_LABEL,
    })


@pbuser_required
def profile_create_view(request):
    pb_user = request.pb_user

    if request.method == "POST":
        form = ProfileForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"].strip()
            # Check for duplicate name
            if Profile.objects.filter(user=pb_user, name__iexact=name).exists():
                messages.error(request, f"A profile named '{name}' already exists.")
            else:
                Profile.objects.create(
                    user=pb_user,
                    name=name,
                    keywords=form.cleaned_data["keywords"],
                    categories=form.cleaned_data["categories"],
                    frequency=form.cleaned_data["frequency"],
                    threshold=form.cleaned_data["threshold"],
                    top_x=form.cleaned_data["top_x"],
                )
                messages.success(request, f"Profile '{name}' created.")
                return redirect("profile_list")
    else:
        form = ProfileForm()

    return render(request, "profiles/create.html", {
        "pb_user": pb_user,
        "form": form,
        "category_tree_json": json.dumps(ARXIV_CATEGORY_TREE),
    })


@pbuser_required
def profile_edit_view(request, profile_id):
    pb_user = request.pb_user
    profile = get_object_or_404(Profile, pk=profile_id, user=pb_user)

    if request.method == "POST":
        form = ProfileForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data["name"].strip()
            dup = Profile.objects.filter(user=pb_user, name__iexact=name).exclude(pk=profile.pk)
            if dup.exists():
                messages.error(request, f"A profile named '{name}' already exists.")
            else:
                profile.name = name
                profile.keywords = form.cleaned_data["keywords"]
                profile.categories = form.cleaned_data["categories"]
                profile.frequency = form.cleaned_data["frequency"]
                profile.threshold = form.cleaned_data["threshold"]
                profile.top_x = form.cleaned_data["top_x"]
                profile.save()
                messages.success(request, f"Profile '{name}' updated.")
                return redirect("profile_list")
    else:
        form = ProfileForm(initial={
            "name": profile.name,
            "frequency": profile.frequency,
            "threshold": profile.threshold or "medium",
            "top_x": profile.top_x or 10,
            "keywords": ", ".join(profile.keywords or []),
            "categories": ",".join(profile.categories or []),
        })

    return render(request, "profiles/create.html", {
        "pb_user": pb_user,
        "form": form,
        "editing": True,
        "profile": profile,
        "category_tree_json": json.dumps(ARXIV_CATEGORY_TREE),
        "initial_categories_json": json.dumps(profile.categories or []),
    })


@pbuser_required
@require_POST
def profile_delete_view(request, profile_id):
    pb_user = request.pb_user
    profile = get_object_or_404(Profile, pk=profile_id, user=pb_user)
    name = profile.name
    profile.delete()
    messages.success(request, f"Profile '{name}' deleted.")
    return redirect("profile_list")


# ── Paper uploads (within a profile) ──────────────────────────────────────

@pbuser_required
@require_POST
def paper_upload_view(request, profile_id):
    """Upload PDF files into a profile's directory."""
    pb_user = request.pb_user
    profile = get_object_or_404(Profile, pk=profile_id, user=pb_user)

    pdf_dir = django_settings.USER_PDF_DIR / str(pb_user.pk) / str(profile.pk)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    uploaded = request.FILES.getlist("files")
    count = 0
    for f in uploaded:
        if f.name.endswith(".pdf"):
            dest = pdf_dir / f.name
            with open(dest, "wb") as out:
                for chunk in f.chunks():
                    out.write(chunk)
            count += 1

    if count:
        messages.success(request, f"Uploaded {count} PDF(s).")
    else:
        messages.warning(request, "No valid PDF files selected.")

    return redirect("profile_list")


@pbuser_required
@require_POST
def paper_delete_view(request, profile_id, filename):
    """Delete a single uploaded PDF."""
    pb_user = request.pb_user
    profile = get_object_or_404(Profile, pk=profile_id, user=pb_user)
    pdf_path = django_settings.USER_PDF_DIR / str(pb_user.pk) / str(profile.pk) / filename

    if pdf_path.exists():
        pdf_path.unlink()
        messages.success(request, f"Deleted {filename}.")
    else:
        messages.error(request, "File not found.")

    return redirect("profile_list")


@pbuser_required
@require_POST
def paper_add_arxiv_view(request, profile_id):
    """Add papers from arXiv by ID – downloads the PDF into the profile dir."""
    import requests as http_requests

    pb_user = request.pb_user
    profile = get_object_or_404(Profile, pk=profile_id, user=pb_user)

    raw = request.POST.get("arxiv_ids", "")
    arxiv_ids = _parse_arxiv_ids(raw)

    if not arxiv_ids:
        messages.error(request, "No valid arXiv IDs provided.")
        return redirect("profile_list")

    pdf_dir = django_settings.USER_PDF_DIR / str(pb_user.pk) / str(profile.pk)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    success = 0
    for aid in arxiv_ids:
        try:
            resp = http_requests.get(f"https://arxiv.org/pdf/{aid}.pdf", timeout=30)
            resp.raise_for_status()
            if "application/pdf" in resp.headers.get("Content-Type", ""):
                (pdf_dir / f"{aid}.pdf").write_bytes(resp.content)
                success += 1
        except Exception:
            messages.warning(request, f"Failed to download {aid}.")

    if success:
        messages.success(request, f"Added {success} paper(s) from arXiv.")

    return redirect("profile_list")


def _parse_arxiv_ids(raw: str) -> list[str]:
    """Extract valid arXiv IDs from free-form input."""
    ids = []
    for line in raw.replace(",", "\n").splitlines():
        token = line.strip()
        if not token:
            continue
        # Strip URL prefixes
        token = re.sub(r"https?://arxiv\.org/(abs|pdf)/", "", token)
        if token.lower().startswith("arxiv:"):
            token = token[6:]
        # Strip version suffix and .pdf
        token = re.sub(r"v\d+$", "", token).replace(".pdf", "")
        if ARXIV_ID_RE.match(token) and token not in ids:
            ids.append(token)
    return ids


# ── Recommendations ────────────────────────────────────────────────────────

@pbuser_required
def recommendations_view(request):
    pb_user = request.pb_user
    profiles = Profile.objects.filter(user=pb_user).order_by("name")

    if not profiles.exists():
        return render(request, "recommendations/list.html", {
            "pb_user": pb_user,
            "profiles": [],
            "recommendations": [],
        })

    # Selected profile (from GET param)
    selected_id = request.GET.get("profile")
    if selected_id:
        try:
            selected_profile = profiles.get(pk=int(selected_id))
        except (Profile.DoesNotExist, ValueError):
            selected_profile = profiles.first()
    else:
        selected_profile = profiles.first()

    # Query recommendations for this profile
    recs = _query_profile_recommendations(pb_user, selected_profile)

    # Apply filters
    min_score = float(request.GET.get("min_score", 0))
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    keyword = request.GET.get("q", "").strip()
    cat_filter = request.GET.getlist("cat")
    page = int(request.GET.get("page", 1))

    if min_score > 0:
        recs = [r for r in recs if r["score"] >= min_score]
    if date_from:
        try:
            df = datetime.strptime(date_from, "%Y-%m-%d").date()
            recs = [r for r in recs if r.get("date_obj") and r["date_obj"] >= df]
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d").date()
            recs = [r for r in recs if r.get("date_obj") and r["date_obj"] <= dt]
        except ValueError:
            pass
    if keyword:
        kw = keyword.lower()
        recs = [
            r for r in recs
            if kw in r["title"].lower() or kw in r.get("abstract", "").lower()
        ]
    if cat_filter:
        recs = [
            r for r in recs
            if any(c in r.get("categories", []) for c in cat_filter)
        ]

    # Score range for slider
    all_scores = [r["score"] for r in recs] if recs else []
    score_min = min(all_scores) if all_scores else 0.0
    score_max = max(all_scores) if all_scores else 1.0

    # Paginate (20 per page)
    per_page = 20
    total = len(recs)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    page_recs = recs[(page - 1) * per_page: page * per_page]

    # Group by date for display
    grouped = defaultdict(list)
    for r in page_recs:
        grouped[r.get("date_str", "Unknown Date")].append(r)

    return render(request, "recommendations/list.html", {
        "pb_user": pb_user,
        "profiles": profiles,
        "selected_profile": selected_profile,
        "grouped_recs": dict(grouped),
        "total_count": total,
        "page": page,
        "total_pages": total_pages,
        "pages_range": range(1, total_pages + 1),
        "score_min": score_min,
        "score_max": score_max,
        "filter_min_score": min_score,
        "filter_date_from": date_from or "",
        "filter_date_to": date_to or "",
        "filter_keyword": keyword,
        "filter_cats": cat_filter,
        "profile_categories": selected_profile.categories or [],
        "code_to_label": ARXIV_CODE_TO_LABEL,
    })


def _query_profile_recommendations(pb_user, profile):
    """
    Fetch recommendations for a profile via the same logic as the
    FastAPI ``/recommendations/profile/{id}`` endpoint.
    """
    corpus_name = f"user_{pb_user.pk}_profile_{profile.pk}"
    try:
        user_corpus = Corpus.objects.get(user=pb_user, name=corpus_name)
    except Corpus.DoesNotExist:
        return []

    # Get runs that used this user corpus
    runs = RecommendationRun.objects.filter(user_corpus=user_corpus)
    recs_qs = (
        Recommendation.objects.filter(run__in=runs)
        .select_related("paper", "run")
        .order_by("-score")
    )

    # Deduplicate by arxiv_id keeping highest score
    seen = {}
    for rec in recs_qs[:5000]:
        paper = rec.paper
        aid = paper.arxiv_id or f"_pk_{paper.pk}"
        if aid in seen and rec.score <= seen[aid]["score"]:
            continue

        dt = paper.submitted_date
        date_obj = dt.date() if dt else None
        date_str = dt.strftime("%d %B %Y") if dt else "Unknown Date"

        summary_text = ""
        try:
            s = Summary.objects.filter(paper=paper, mode="abstract").first()
            if s:
                summary_text = s.summary_text or ""
        except Exception:
            pass

        seen[aid] = {
            "title": paper.title,
            "score": rec.score,
            "rank": rec.rank,
            "arxiv_id": paper.arxiv_id,
            "abstract": paper.abstract or "",
            "summary_text": summary_text,
            "date_obj": date_obj,
            "date_str": date_str,
            "categories": paper.categories_list,
            "total_papers_fetched": rec.run.total_papers_fetched,
        }

    return sorted(seen.values(), key=lambda x: x["score"], reverse=True)


# ── Settings ───────────────────────────────────────────────────────────────

@pbuser_required
def settings_view(request):
    pb_user = request.pb_user

    if request.method == "POST":
        form = UserSettingsForm(request.POST)
        if form.is_valid():
            pb_user.name = form.cleaned_data["name"]
            new_email = form.cleaned_data["email"]
            if new_email != pb_user.email:
                if PBUser.objects.filter(email__iexact=new_email).exclude(pk=pb_user.pk).exists():
                    messages.error(request, "That email is already taken.")
                else:
                    pb_user.email = new_email
            pb_user.save()
            login_pbuser(request, pb_user)  # refresh session
            messages.success(request, "Settings updated.")
            return redirect("settings")
    else:
        form = UserSettingsForm(initial={"name": pb_user.name or "", "email": pb_user.email})

    return render(request, "settings.html", {"pb_user": pb_user, "form": form})


# ── Help page ──────────────────────────────────────────────────────────────

def help_view(request):
    return render(request, "help.html", {"pb_user": get_current_pbuser(request)})
