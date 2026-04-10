from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    PBUser, Profile, Corpus, Paper, Section,
    Summary, RecommendationRun, Recommendation,
)


@admin.register(PBUser)
class PBUserAdmin(BaseUserAdmin):
    """Admin for the custom email-based user model."""

    list_display = ("id", "email", "name", "is_staff", "is_active", "created_at")
    search_fields = ("email", "name")
    ordering = ("-created_at",)

    # Fields shown when editing an existing user
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("name",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )

    # Fields shown when creating a new user via admin
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "name", "password1", "password2", "is_staff", "is_superuser"),
        }),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "name", "frequency", "threshold", "top_x")
    list_filter = ("frequency",)
    search_fields = ("name",)


@admin.register(Corpus)
class CorpusAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "name", "created_at")
    search_fields = ("name",)


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ("id", "arxiv_id", "title_short", "source", "submitted_date")
    list_filter = ("source",)
    search_fields = ("arxiv_id", "title")

    @admin.display(description="Title")
    def title_short(self, obj):
        return obj.title[:80]


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("id", "run", "paper", "score", "rank")
    list_filter = ("run",)


@admin.register(RecommendationRun)
class RecommendationRunAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "profile", "target_date", "total_papers_fetched")
