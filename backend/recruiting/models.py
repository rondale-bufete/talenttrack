from django.core.exceptions import ValidationError
from django.db import models


class Job(models.Model):
    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full-time"
        PART_TIME = "part_time", "Part-time"
        CONTRACT = "contract", "Contract"

    title = models.CharField(max_length=120)
    department = models.CharField(max_length=80, blank=True)
    location = models.CharField(max_length=80, default="Remote")
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    description = models.TextField(blank=True)
    # Stored as a list of lowercase strings, e.g. ["django", "react", "selenium"]
    required_skills = models.JSONField(default=list, blank=True)
    min_years_experience = models.PositiveSmallIntegerField(default=0)
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Candidate(models.Model):
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    skills = models.JSONField(default=list, blank=True)
    years_experience = models.PositiveSmallIntegerField(default=0)
    resume_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class Application(models.Model):
    """A candidate applying to a job. Moves through a fixed hiring pipeline."""

    class Status(models.TextChoices):
        APPLIED = "applied", "Applied"
        SCREENING = "screening", "Screening"
        INTERVIEW = "interview", "Interview"
        OFFER = "offer", "Offer"
        HIRED = "hired", "Hired"
        REJECTED = "rejected", "Rejected"

    # Which status can move to which. A business rule worth testing.
    ALLOWED_TRANSITIONS = {
        Status.APPLIED: {Status.SCREENING, Status.REJECTED},
        Status.SCREENING: {Status.INTERVIEW, Status.REJECTED},
        Status.INTERVIEW: {Status.OFFER, Status.REJECTED},
        Status.OFFER: {Status.HIRED, Status.REJECTED},
        Status.HIRED: set(),
        Status.REJECTED: set(),
    }
    # The "happy path" next step, used by the Advance button
    NEXT_STATUS = {
        Status.APPLIED: Status.SCREENING,
        Status.SCREENING: Status.INTERVIEW,
        Status.INTERVIEW: Status.OFFER,
        Status.OFFER: Status.HIRED,
    }

    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name="applications")
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)
    match_score = models.PositiveSmallIntegerField(null=True, blank=True)  # 0-100, set by screening
    skills_verified = models.BooleanField(null=True, blank=True)
    notes = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-applied_at"]
        constraints = [
            models.UniqueConstraint(fields=["candidate", "job"], name="unique_application_per_job")
        ]

    def __str__(self):
        return f"{self.candidate} -> {self.job} ({self.status})"

    def can_transition_to(self, new_status):
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status):
        if new_status == self.status:
            return
        if not self.can_transition_to(new_status):
            raise ValidationError(f"Cannot move application from '{self.status}' to '{new_status}'.")
        self.status = new_status

    def advance(self):
        nxt = self.NEXT_STATUS.get(self.status)
        if nxt is None:
            raise ValidationError(f"Application in '{self.status}' cannot be advanced.")
        self.transition_to(nxt)
