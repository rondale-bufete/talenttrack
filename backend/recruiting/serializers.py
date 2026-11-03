from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Application, Candidate, Job
from .screening import normalize_skills


class SkillsField(serializers.ListField):
    """Accepts ["Django", " react "] and stores ["django", "react"] (sorted, unique)."""

    child = serializers.CharField(max_length=40)

    def to_internal_value(self, data):
        return sorted(normalize_skills(super().to_internal_value(data)))


class JobSerializer(serializers.ModelSerializer):
    required_skills = SkillsField(required=False)
    application_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Job
        fields = [
            "id", "title", "department", "location", "employment_type", "description",
            "required_skills", "min_years_experience", "is_open", "created_at",
            "application_count",
        ]


class CandidateSerializer(serializers.ModelSerializer):
    skills = SkillsField(required=False)

    class Meta:
        model = Candidate
        fields = [
            "id", "full_name", "email", "phone", "skills", "years_experience",
            "resume_url", "created_at",
        ]

    def validate_email(self, value):
        # The built-in unique check is case-sensitive; emails are not.
        value = value.lower()
        qs = Candidate.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A candidate with this email already exists.")
        return value


class ApplicationSerializer(serializers.ModelSerializer):
    candidate_name = serializers.CharField(source="candidate.full_name", read_only=True)
    job_title = serializers.CharField(source="job.title", read_only=True)

    class Meta:
        model = Application
        fields = [
            "id", "candidate", "candidate_name", "job", "job_title", "status",
            "match_score", "skills_verified", "notes", "applied_at", "updated_at",
        ]
        read_only_fields = ["match_score", "skills_verified", "applied_at", "updated_at"]

    def validate(self, attrs):
        job = attrs.get("job") or getattr(self.instance, "job", None)
        if self.instance is None and job is not None and not job.is_open:
            raise serializers.ValidationError({"job": "This job is closed to new applications."})

        new_status = attrs.get("status")
        if self.instance is None:
            # New applications always start at "applied"
            attrs["status"] = Application.Status.APPLIED
        elif new_status and new_status != self.instance.status:
            if not self.instance.can_transition_to(new_status):
                raise serializers.ValidationError(
                    {"status": f"Cannot move from '{self.instance.status}' to '{new_status}'."}
                )
        return attrs


class StatusChangeSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Application.Status.choices)

    def apply(self, application):
        try:
            application.transition_to(self.validated_data["status"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"status": exc.messages}) from exc
        application.save(update_fields=["status", "updated_at"])
        return application
