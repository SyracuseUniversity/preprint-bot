"""
Django ORM models mapped to the existing preprint_bot PostgreSQL schema.

Every model uses ``managed = False`` so that ``migrate`` never touches
the tables that were created by ``database_schema.sql``.
"""

from django.db import models
from django.contrib.postgres.fields import ArrayField


# ── Users ──────────────────────────────────────────────────────────────────

class PBUser(models.Model):
    """Maps to the public.users table."""

    email = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    password_hash = models.TextField(default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "users"

    def __str__(self):
        return self.name or self.email


# ── Profiles ───────────────────────────────────────────────────────────────

class Profile(models.Model):
    """Maps to the public.profiles table."""

    user = models.ForeignKey(PBUser, on_delete=models.CASCADE, related_name="profiles")
    name = models.CharField(max_length=255)
    keywords = ArrayField(models.TextField(), default=list, blank=True)
    categories = ArrayField(models.TextField(), default=list, blank=True)
    email_notify = models.BooleanField(default=True)
    frequency = models.CharField(max_length=20, default="weekly")
    threshold = models.CharField(max_length=20, default="medium")
    top_x = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "profiles"
        unique_together = [("user", "name")]

    def __str__(self):
        return f"{self.name} ({self.user})"


# ── Corpora ────────────────────────────────────────────────────────────────

class Corpus(models.Model):
    """Maps to the public.corpora table."""

    user = models.ForeignKey(PBUser, on_delete=models.CASCADE, related_name="corpora")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "corpora"
        unique_together = [("user", "name")]
        verbose_name_plural = "corpora"

    def __str__(self):
        return self.name


# ── Profile ↔ Corpus junction ─────────────────────────────────────────────

class ProfileCorpus(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "profile_corpora"
        unique_together = [("profile", "corpus")]


# ── Papers ─────────────────────────────────────────────────────────────────

class Paper(models.Model):
    """Maps to the public.papers table."""

    corpus = models.ForeignKey(Corpus, on_delete=models.CASCADE, related_name="papers")
    arxiv_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    title = models.TextField()
    abstract = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True, null=True)  # jsonb
    pdf_path = models.TextField(blank=True, null=True)
    processed_text_path = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=20, default="arxiv")
    submitted_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "papers"

    def __str__(self):
        return self.title[:80]

    @property
    def arxiv_url(self):
        if self.arxiv_id:
            return f"https://arxiv.org/abs/{self.arxiv_id}"
        return ""

    @property
    def categories_list(self):
        """Extract categories from the metadata JSON."""
        if self.metadata and isinstance(self.metadata, dict):
            return self.metadata.get("categories", [])
        return []


# ── Sections ───────────────────────────────────────────────────────────────

class Section(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name="sections")
    section_header = models.TextField(blank=True, null=True)
    section_text = models.TextField(blank=True, null=True)
    section_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "sections"


# ── Summaries ──────────────────────────────────────────────────────────────

class Summary(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name="summaries")
    mode = models.CharField(max_length=20, default="abstract")
    summary_text = models.TextField(blank=True, null=True)
    summarizer = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "summaries"
        unique_together = [("paper", "mode")]
        verbose_name_plural = "summaries"


# ── Recommendation runs ───────────────────────────────────────────────────

class RecommendationRun(models.Model):
    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, blank=True, null=True, related_name="runs"
    )
    user = models.ForeignKey(PBUser, on_delete=models.CASCADE, related_name="recommendation_runs")
    user_corpus = models.ForeignKey(
        Corpus, on_delete=models.CASCADE, related_name="user_runs"
    )
    ref_corpus = models.ForeignKey(
        Corpus, on_delete=models.CASCADE, related_name="ref_runs"
    )
    threshold = models.CharField(max_length=20, blank=True, null=True)
    method = models.CharField(max_length=20, blank=True, null=True)
    total_papers_fetched = models.IntegerField(default=0)
    target_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "recommendation_runs"


# ── Recommendations ────────────────────────────────────────────────────────

class Recommendation(models.Model):
    run = models.ForeignKey(
        RecommendationRun, on_delete=models.CASCADE, related_name="recommendations"
    )
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name="recommendations")
    score = models.FloatField()
    rank = models.IntegerField()
    summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "recommendations"
        unique_together = [("run", "paper")]


# ── Profile ↔ Recommendation junction ─────────────────────────────────────

class ProfileRecommendation(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    recommendation = models.ForeignKey(Recommendation, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "profile_recommendations"
        unique_together = [("profile", "recommendation")]


# ── Auth tokens ────────────────────────────────────────────────────────────

class AuthToken(models.Model):
    user = models.ForeignKey(PBUser, on_delete=models.CASCADE, related_name="auth_tokens")
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "auth_tokens"


# ── Password resets ────────────────────────────────────────────────────────

class PasswordReset(models.Model):
    user = models.ForeignKey(PBUser, on_delete=models.CASCADE, related_name="password_resets")
    token = models.TextField(unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "password_resets"


# ── Email logs ─────────────────────────────────────────────────────────────

class EmailLog(models.Model):
    user = models.ForeignKey(PBUser, on_delete=models.CASCADE, related_name="email_logs")
    profile = models.ForeignKey(
        Profile, on_delete=models.SET_NULL, blank=True, null=True
    )
    subject = models.TextField(blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default="sent")
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "email_logs"
