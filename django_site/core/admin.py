from django.contrib import admin
from .models import (
    PBUser, Profile, Corpus, Paper, Section,
    Summary, RecommendationRun, Recommendation,
)


@admin.register(PBUser)
class PBUserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "name", "created_at")
    search_fields = ("email", "name")


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
