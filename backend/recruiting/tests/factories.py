"""Tiny helpers that create valid objects, so each test only states what it cares about."""
import itertools

from recruiting.models import Application, Candidate, Job

_seq = itertools.count(1)


def make_job(**kw):
    defaults = dict(title="QA Engineer", required_skills=["selenium", "python"], min_years_experience=1)
    defaults.update(kw)
    return Job.objects.create(**defaults)


def make_candidate(**kw):
    n = next(_seq)
    defaults = dict(full_name=f"Candidate {n}", email=f"c{n}@example.com",
                    skills=["python"], years_experience=1)
    defaults.update(kw)
    return Candidate.objects.create(**defaults)


def make_application(candidate=None, job=None, **kw):
    return Application.objects.create(
        candidate=candidate or make_candidate(), job=job or make_job(), **kw
    )
