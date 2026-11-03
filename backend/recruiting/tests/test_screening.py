"""
Tests for the multithreaded screener.

Notice the fake verifiers: tests never hit the network (fast + deterministic).
"""
import threading
import time

import pytest

from recruiting.models import Application
from recruiting.screening import BulkScreener, ProgressCounter, compute_match_score
from .factories import make_application, make_candidate, make_job


# ------------------------------------------------------------- pure functions
@pytest.mark.parametrize("cand, req, years, min_years, expected", [
    (["django", "react"], ["django", "react"], 3, 1, 100),   # perfect match
    ([], ["django", "react"], 0, 2, 0),                       # nothing matches
    (["Django"], ["django", "react"], 1, 1, 65),               # 1/2 skills (35) + full exp (30)
    (["django", "react"], ["django", "react"], 1, 2, 85),      # all skills (70) + half exp (15)
    (["anything"], [], 0, 0, 100),                             # job requires nothing
])
def test_compute_match_score(cand, req, years, min_years, expected):
    assert compute_match_score(cand, req, years, min_years) == expected


def test_progress_counter_is_thread_safe():
    counter = ProgressCounter(total=10_000)

    def work():
        for _ in range(1_000):
            counter.increment()

    threads = [threading.Thread(target=work) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert counter.done == 10_000   # no lost updates


# ------------------------------------------------------------- the screener
def _apps_for(job, n):
    for i in range(n):
        make_application(make_candidate(skills=["selenium", "python"], years_experience=2), job)
    return job.applications.select_related("candidate", "job")


@pytest.mark.django_db
def test_screening_saves_scores_to_the_database():
    job = make_job(required_skills=["selenium", "python"], min_years_experience=1)
    apps = _apps_for(job, 3)

    report = BulkScreener(verifier=lambda email, skills: True, max_workers=4).run(apps)

    assert report.screened == 3 and report.failed == 0
    assert set(Application.objects.values_list("match_score", flat=True)) == {100}
    assert all(Application.objects.values_list("skills_verified", flat=True))


@pytest.mark.django_db
def test_threads_run_in_parallel_and_are_faster_than_sequential():
    job = make_job()
    apps = _apps_for(job, 8)

    def slow_verifier(email, skills):
        time.sleep(0.1)   # simulates network latency; releases the GIL
        return True

    screener = BulkScreener(verifier=slow_verifier, max_workers=8)
    seq = screener.run(apps, sequential=True)
    par = screener.run(apps)

    assert seq.elapsed_ms >= 800          # 8 x 100 ms one after another
    assert par.elapsed_ms < 400           # overlapping waits
    assert par.workers == 8


@pytest.mark.django_db
def test_uses_multiple_worker_threads():
    job = make_job()
    apps = _apps_for(job, 6)
    seen = set()
    lock = threading.Lock()

    def recording_verifier(email, skills):
        time.sleep(0.05)
        with lock:
            seen.add(threading.current_thread().name)
        return True

    BulkScreener(verifier=recording_verifier, max_workers=3).run(apps)
    assert len(seen) > 1
    assert all(name.startswith("screener") for name in seen)


@pytest.mark.django_db
def test_one_failure_does_not_stop_the_batch():
    job = make_job()
    bad = make_application(make_candidate(email="broken@example.com"), job)
    _apps_for(job, 3)

    def flaky_verifier(email, skills):
        if email == "broken@example.com":
            raise ConnectionError("verification API timed out")
        return True

    report = BulkScreener(verifier=flaky_verifier).run(job.applications.select_related("candidate", "job"))

    assert report.screened == 3 and report.failed == 1
    failed = next(r for r in report.results if r.error)
    assert failed.application_id == bad.id and "timed out" in failed.error
    bad.refresh_from_db()
    assert bad.match_score is None   # untouched


@pytest.mark.django_db
def test_screening_an_empty_job_is_fine():
    report = BulkScreener(verifier=lambda e, s: True).run(Application.objects.none())
    assert report.screened == 0 and report.results == []
