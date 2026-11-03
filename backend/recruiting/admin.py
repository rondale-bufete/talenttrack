from django.contrib import admin

from .models import Application, Candidate, Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ["title", "department", "location", "is_open", "created_at"]
    list_filter = ["is_open", "employment_type"]
    search_fields = ["title"]


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "years_experience"]
    search_fields = ["full_name", "email"]


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ["candidate", "job", "status", "match_score", "applied_at"]
    list_filter = ["status", "job"]
    list_select_related = ["candidate", "job"]
