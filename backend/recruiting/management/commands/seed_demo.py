import random

from django.core.management.base import BaseCommand
from django.db import transaction

from recruiting.models import Application, Candidate, Job

SKILL_POOL = [
    "python", "django", "react", "redux", "javascript", "typescript", "selenium",
    "gcp", "docker", "sql", "git", "rest", "pytest", "kotlin", "php",
]
FIRST = ["Ana", "Mark", "Liza", "Paolo", "Joy", "Carlo", "Bea", "Rico", "Mae", "Jun"]
LAST = ["Reyes", "Santos", "Cruz", "Bautista", "Garcia", "Mendoza", "Torres", "Ramos"]


class Command(BaseCommand):
    help = "Create demo jobs, candidates and applications."

    def add_arguments(self, parser):
        parser.add_argument("--candidates", type=int, default=40)
        parser.add_argument("--reset", action="store_true", help="Delete existing data first")

    @transaction.atomic
    def handle(self, *args, **opts):
        if opts["reset"]:
            Application.objects.all().delete()
            Candidate.objects.all().delete()
            Job.objects.all().delete()

        rng = random.Random(42)  # fixed seed -> same demo data every time
        jobs = [
            Job.objects.create(
                title="Software Developer / QA Automation Engineer", department="Engineering",
                required_skills=["django", "react", "redux", "gcp", "selenium"],
                min_years_experience=1,
                description="Build and test our talent platform.",
            ),
            Job.objects.create(
                title="Backend Engineer", department="Engineering",
                required_skills=["python", "django", "sql", "docker"], min_years_experience=2,
            ),
            Job.objects.create(
                title="Frontend Engineer", department="Engineering",
                required_skills=["react", "redux", "typescript"], min_years_experience=1,
            ),
        ]

        candidates = []
        for i in range(opts["candidates"]):
            name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
            candidates.append(Candidate(
                full_name=name,
                email=f"{name.lower().replace(' ', '.')}.{i}@example.com",
                skills=sorted(rng.sample(SKILL_POOL, rng.randint(2, 7))),
                years_experience=rng.randint(0, 6),
            ))
        Candidate.objects.bulk_create(candidates)

        apps = []
        for c in Candidate.objects.all():
            for job in rng.sample(jobs, rng.randint(1, 2)):
                apps.append(Application(candidate=c, job=job))
        Application.objects.bulk_create(apps)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(jobs)} jobs, {len(candidates)} candidates, {len(apps)} applications."
        ))
