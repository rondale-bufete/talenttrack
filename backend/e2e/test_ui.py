"""
End-to-end browser tests. Run them with:   pytest -m e2e
Watch the browser while they run:          HEADED=1 pytest -m e2e

Test data that is not the subject of the test is created through the ORM (fast);
only the behaviour under test is driven through the browser.
"""
import pytest

from recruiting.models import Application
from recruiting.tests.factories import make_application, make_candidate, make_job
from .pages.app_pages import CandidatesPage, DashboardPage, JobsPage, PipelinePage

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]


@pytest.fixture(autouse=True)
def instant_verifier(monkeypatch):
    """The live server runs in this same process, so we can stub the slow external call."""
    monkeypatch.setattr("recruiting.screening.simulated_skills_verifier", lambda email, skills: True)


# ----------------------------------------------------------------- smoke
def test_dashboard_shows_live_counts(browser, base_url):
    job = make_job()
    make_application(job=job)
    make_application(job=job, status=Application.Status.HIRED)

    page = DashboardPage(browser, base_url).open()

    assert page.stat("open-jobs") == 1
    assert page.stat("applications") == 2
    assert page.stat("hired") == 1


# ----------------------------------------------------------------- jobs
def test_post_a_job(browser, base_url):
    page = JobsPage(browser, base_url).open()

    page.create_job("QA Automation Engineer", "Engineering", "Selenium, Python", 1)

    page.wait_for_job("QA Automation Engineer")
    assert page.job_titles() == ["QA Automation Engineer"]


def test_job_form_shows_server_validation_error(browser, base_url):
    page = JobsPage(browser, base_url).open()
    page.create_job(title="")                       # negative test: required field missing
    assert "title" in page.form_error().lower()


def test_screening_from_jobs_page_reports_thread_usage(browser, base_url):
    job = make_job(title="Django Dev", required_skills=["django"])
    for _ in range(3):
        make_application(job=job)

    message = JobsPage(browser, base_url).open().run_screening("Django Dev")

    assert "Screened 3 applicants" in message
    assert "threads" in message


# ----------------------------------------------------------------- candidates
def test_add_candidate_and_filter(browser, base_url):
    make_candidate(full_name="Existing Person", skills=["php"])
    page = CandidatesPage(browser, base_url).open()

    page.add("Ana Reyes", "ana@example.com", "django, react", 2)
    page.wait_for_candidate("Ana Reyes")

    page.filter("react")
    page.wait.until(lambda d: page.names() == ["Ana Reyes"])


def test_duplicate_email_is_rejected(browser, base_url):
    make_candidate(email="taken@example.com")
    page = CandidatesPage(browser, base_url).open()

    page.add("Someone", "TAKEN@example.com")

    assert "already exists" in page.form_error()


# ----------------------------------------------------------------- pipeline (regression flow)
def test_full_hiring_flow(browser, base_url):
    job = make_job(title="QA Engineer")
    make_candidate(full_name="Ana Reyes")
    page = PipelinePage(browser, base_url).open_for_job(job.id)

    page.add_applicant("Ana Reyes")
    for frm, to in [("applied", "screening"), ("screening", "interview"),
                    ("interview", "offer"), ("offer", "hired")]:
        page.advance("Ana Reyes", frm, to)

    assert page.names_in("hired") == ["Ana Reyes"]
    assert Application.objects.get().status == "hired"      # UI and DB agree


def test_reject_applicant(browser, base_url):
    app = make_application(make_candidate(full_name="Mark Cruz"), make_job())
    page = PipelinePage(browser, base_url).open_for_job(app.job_id)

    page.reject("Mark Cruz", "applied")

    assert page.names_in("applied") == []


def test_scores_appear_after_screening(browser, base_url):
    job = make_job(required_skills=["python", "selenium"], min_years_experience=1)
    make_application(make_candidate(full_name="Strong Match", skills=["python", "selenium"],
                                    years_experience=3), job)
    make_application(make_candidate(full_name="Weak Match", skills=["php"],
                                    years_experience=0), job)
    page = PipelinePage(browser, base_url).open_for_job(job.id)
    page.wait_for_card("Weak Match", "applied")

    page.score_all()

    page.wait_for_score("Strong Match", "applied", 100)
    page.wait_for_score("Weak Match", "applied", 0)
    assert page.names_in("applied") == ["Strong Match", "Weak Match"]   # sorted best first
