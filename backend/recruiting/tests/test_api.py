"""Integration tests: real HTTP requests through URL routing, serializers, views and DB."""
import pytest
from rest_framework.test import APIClient

from recruiting.models import Application
from .factories import make_application, make_candidate, make_job

pytestmark = pytest.mark.django_db


@pytest.fixture
def api():
    return APIClient()


# ------------------------------------------------------------------ jobs
def test_create_job_normalizes_skills(api):
    res = api.post("/api/jobs/", {"title": "QA", "required_skills": [" Selenium", "PYTHON", "python"]},
                   format="json")
    assert res.status_code == 201
    assert res.json()["required_skills"] == ["python", "selenium"]


def test_job_title_is_required(api):
    res = api.post("/api/jobs/", {"department": "Eng"}, format="json")
    assert res.status_code == 400
    assert "title" in res.json()


def test_list_jobs_filters_open_and_counts_applications(api):
    open_job = make_job(title="Open")
    make_job(title="Closed", is_open=False)
    make_application(job=open_job)

    data = api.get("/api/jobs/?is_open=true").json()

    assert data["count"] == 1
    assert data["results"][0]["title"] == "Open"
    assert data["results"][0]["application_count"] == 1


def test_search_jobs(api):
    make_job(title="Django Developer")
    make_job(title="Office Manager")
    titles = [j["title"] for j in api.get("/api/jobs/?search=django").json()["results"]]
    assert titles == ["Django Developer"]


# ------------------------------------------------------------------ candidates
def test_duplicate_candidate_email_rejected(api):
    make_candidate(email="ana@example.com")
    res = api.post("/api/candidates/", {"full_name": "Ana", "email": "ANA@example.com"}, format="json")
    assert res.status_code == 400
    assert "email" in res.json()


# ------------------------------------------------------------------ applications
def test_apply_and_advance_through_pipeline(api):
    cand, job = make_candidate(), make_job()
    res = api.post("/api/applications/", {"candidate": cand.id, "job": job.id, "status": "hired"},
                   format="json")
    assert res.status_code == 201
    assert res.json()["status"] == "applied"           # client can't skip ahead
    app_id = res.json()["id"]

    for expected in ["screening", "interview", "offer", "hired"]:
        res = api.post(f"/api/applications/{app_id}/advance/")
        assert res.status_code == 200
        assert res.json()["status"] == expected

    res = api.post(f"/api/applications/{app_id}/advance/")
    assert res.status_code == 400                       # hired is final


def test_cannot_apply_twice(api):
    app = make_application()
    res = api.post("/api/applications/", {"candidate": app.candidate_id, "job": app.job_id},
                   format="json")
    assert res.status_code == 400


def test_cannot_apply_to_closed_job(api):
    job = make_job(is_open=False)
    res = api.post("/api/applications/", {"candidate": make_candidate().id, "job": job.id},
                   format="json")
    assert res.status_code == 400
    assert "closed" in str(res.json())


def test_invalid_status_jump_rejected(api):
    app = make_application()
    res = api.post(f"/api/applications/{app.id}/status/", {"status": "offer"}, format="json")
    assert res.status_code == 400
    res = api.post(f"/api/applications/{app.id}/status/", {"status": "rejected"}, format="json")
    assert res.status_code == 200 and res.json()["status"] == "rejected"


def test_filter_applications_by_status(api):
    job = make_job()
    make_application(job=job, status=Application.Status.INTERVIEW)
    make_application(job=job)
    data = api.get(f"/api/applications/?job={job.id}&status=interview").json()
    assert data["count"] == 1


def test_list_applications_uses_constant_queries(api, django_assert_max_num_queries):
    """select_related prevents the N+1 problem: query count must not grow with rows."""
    job = make_job()
    for _ in range(15):
        make_application(job=job)
    with django_assert_max_num_queries(3):
        api.get("/api/applications/")


# ------------------------------------------------------------------ screening + stats
def test_screen_endpoint(api, monkeypatch):
    monkeypatch.setattr("recruiting.screening.simulated_skills_verifier", lambda e, s: True)
    job = make_job(required_skills=["python"], min_years_experience=0)
    make_application(make_candidate(skills=["python"]), job)
    make_application(make_candidate(skills=["java"]), job)

    data = api.post(f"/api/jobs/{job.id}/screen/").json()

    assert data["screened"] == 2
    assert sorted(r["match_score"] for r in data["results"]) == [30, 100]


def test_stats(api):
    job = make_job()
    make_application(job=job)
    make_application(job=job, status=Application.Status.HIRED)
    data = api.get("/api/stats/").json()
    assert data["open_jobs"] == 1
    assert data["applications"] == 2
    assert data["by_status"]["hired"] == 1


def test_health(api):
    assert api.get("/api/health/").json() == {"status": "ok"}
