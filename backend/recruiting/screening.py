"""
Bulk candidate screening — the multithreading part of the project.

THE SCENARIO
------------
For every application to a job we must:
  1. call an external "skills verification" service (slow network I/O, ~200 ms each), then
  2. compute a 0-100 match score (fast CPU work).

Done one after another, 50 applications x 200 ms = 10 seconds.
Done with a pool of 8 threads, they overlap their waiting: roughly 50 / 8 x 200 ms ~ 1.3 s.

WHY THREADS WORK HERE (the GIL question)
----------------------------------------
CPython's Global Interpreter Lock lets only one thread run Python bytecode at a time.
But a thread that is waiting on the network (or time.sleep, or disk) RELEASES the GIL,
so other threads run while it waits. Threads therefore speed up I/O-bound work.
For CPU-bound work (image processing, heavy math) use multiprocessing / ProcessPoolExecutor.

DESIGN DECISIONS (good things to say in an interview)
-----------------------------------------------------
* Worker threads do NOT touch the database. Django opens one DB connection per thread,
  so writing from workers means many connections and connection leaks if not closed.
  Workers only do I/O + scoring and return plain results; the main thread saves
  everything in ONE bulk_update query.
* Shared state (the progress counter) is protected by a threading.Lock, because
  `count += 1` is read-modify-write and is not atomic across threads.
* One failing verification must not kill the whole batch: each future's exception is
  caught and recorded per application.
* The verifier is injected (dependency injection) so tests can pass a fake one with no
  network calls.
"""
from __future__ import annotations

import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Callable, Iterable

from django.conf import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- pure scoring
def normalize_skills(skills: Iterable[str]) -> set[str]:
    return {s.strip().lower() for s in skills if s and s.strip()}


def compute_match_score(candidate_skills, required_skills, years_experience, min_years) -> int:
    """
    70% weight on skill overlap, 30% on experience. Returns an int 0-100.
    A job with no required skills gives full marks for the skill part.
    """
    required = normalize_skills(required_skills)
    have = normalize_skills(candidate_skills)
    skill_ratio = 1.0 if not required else len(required & have) / len(required)

    if min_years <= 0:
        exp_ratio = 1.0
    else:
        exp_ratio = min(years_experience / min_years, 1.0)

    return round(skill_ratio * 70 + exp_ratio * 30)


# ---------------------------------------------------------------- verification
def simulated_skills_verifier(email: str, skills: list[str]) -> bool:
    """
    Stand-in for an HTTP call to a third-party verification API.
    time.sleep releases the GIL exactly like a real socket read would.
    """
    time.sleep(0.2)
    return bool(skills) and random.random() > 0.1


Verifier = Callable[[str, list], bool]


@dataclass
class ScreeningResult:
    application_id: int
    match_score: int | None = None
    skills_verified: bool | None = None
    error: str | None = None


@dataclass
class ScreeningReport:
    workers: int
    elapsed_ms: int
    results: list[ScreeningResult] = field(default_factory=list)

    @property
    def screened(self):
        return sum(1 for r in self.results if r.error is None)

    @property
    def failed(self):
        return sum(1 for r in self.results if r.error is not None)


class ProgressCounter:
    """Thread-safe counter. Without the lock, two threads can read the same
    value and both write value+1, losing an increment (a race condition)."""

    def __init__(self, total: int):
        self.total = total
        self._done = 0
        self._lock = threading.Lock()

    def increment(self) -> int:
        with self._lock:
            self._done += 1
            return self._done

    @property
    def done(self):
        with self._lock:
            return self._done


# ---------------------------------------------------------------- the screener
class BulkScreener:
    def __init__(self, verifier: Verifier | None = None, max_workers: int | None = None):
        self.verifier = verifier or simulated_skills_verifier
        self.max_workers = max_workers or settings.SCREENING_MAX_WORKERS

    @staticmethod
    def _snapshot(app):
        """Copy what a worker needs into plain data, so workers never touch the ORM."""
        return {
            "id": app.id,
            "email": app.candidate.email,
            "skills": list(app.candidate.skills),
            "years": app.candidate.years_experience,
            "required": list(app.job.required_skills),
            "min_years": app.job.min_years_experience,
        }

    def _screen_one(self, item: dict, progress: ProgressCounter) -> ScreeningResult:
        try:
            verified = self.verifier(item["email"], item["skills"])          # I/O (slow)
            score = compute_match_score(item["skills"], item["required"],
                                        item["years"], item["min_years"])    # CPU (fast)
            return ScreeningResult(item["id"], score, verified)
        finally:
            done = progress.increment()
            logger.debug("screened %s/%s on %s", done, progress.total,
                         threading.current_thread().name)

    def run(self, applications, sequential: bool = False) -> ScreeningReport:
        """
        `applications` is a queryset/list of Application objects with candidate and
        job already loaded (use select_related to avoid N+1 queries).
        `sequential=True` runs without threads, useful for benchmarking.
        """
        apps = list(applications)
        items = [self._snapshot(a) for a in apps]
        progress = ProgressCounter(len(items))
        workers = 1 if sequential else max(1, min(self.max_workers, len(items) or 1))
        start = time.perf_counter()
        results: list[ScreeningResult] = []

        if sequential:
            for item in items:
                try:
                    results.append(self._screen_one(item, progress))
                except Exception as exc:  # noqa: BLE001 - record and continue
                    results.append(ScreeningResult(item["id"], error=str(exc)))
        else:
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="screener") as pool:
                future_to_id = {pool.submit(self._screen_one, it, progress): it["id"] for it in items}
                for future in as_completed(future_to_id):
                    app_id = future_to_id[future]
                    try:
                        results.append(future.result())
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("screening failed for application %s: %s", app_id, exc)
                        results.append(ScreeningResult(app_id, error=str(exc)))

        elapsed_ms = round((time.perf_counter() - start) * 1000)
        self._save(apps, results)
        results.sort(key=lambda r: r.application_id)
        return ScreeningReport(workers=workers, elapsed_ms=elapsed_ms, results=results)

    @staticmethod
    def _save(apps, results):
        """Single-threaded write: one bulk UPDATE instead of N queries from N threads."""
        by_id = {r.application_id: r for r in results if r.error is None}
        changed = []
        for app in apps:
            r = by_id.get(app.id)
            if r:
                app.match_score = r.match_score
                app.skills_verified = r.skills_verified
                changed.append(app)
        if changed:
            type(changed[0]).objects.bulk_update(changed, ["match_score", "skills_verified"])
