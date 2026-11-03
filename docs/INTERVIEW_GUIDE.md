# Interview Study Guide: Software Developer / QA Automation Engineer

How to use this guide: read a section, then open the file it points to and find the
concept in real code. Being able to say *"in my project, I did X in this file because Y"*
is worth more than any definition.

---

## 0. Your 60-second project pitch

> "To get hands-on with this exact stack, I built TalentTrack, a small applicant tracking
> system. The backend is Django with Django REST Framework, the frontend is React with
> Redux Toolkit, and it's containerized and set up to deploy on Google Cloud Run with
> Cloud SQL. The interesting part is bulk screening: scoring every applicant requires a
> slow external API call, so I used a ThreadPoolExecutor to run those calls concurrently,
> which cut the time from about 2.8 seconds to 0.4 for 14 applicants. On the QA side I
> have tests at three levels: pytest unit and API tests, Vitest tests for the Redux
> reducers, and Selenium end-to-end tests built with the Page Object Model, all running
> in CI on every push."

Be honest that it's a learning/portfolio project. Interviewers respect "I didn't know
this stack, so I built something with it" far more than overclaiming.

**Relate it to your real experience too**: you've shipped production work for clients
(full stack, Android/Kotlin, CodeIgniter). Debugging, APIs, Git and working with clients
are skills you already have; this project shows you can pick up new tools quickly.

---

## 1. Django & Django REST Framework

### Core concepts

| Concept | One-line explanation | In the project |
|---|---|---|
| **MVT** | Model (data) – View (logic) – Template (HTML). Django's version of MVC | `models.py`, `views.py` (we return JSON instead of templates) |
| **ORM** | Python classes ↔ database tables; queries without raw SQL | `Application.objects.filter(status="hired")` |
| **Migrations** | Version control for the DB schema | `recruiting/migrations/0001_initial.py` |
| **Serializer** | Converts model ↔ JSON, and **validates input** | `serializers.py` |
| **ViewSet + Router** | One class gives list/create/retrieve/update/delete; router builds URLs | `JobViewSet`, `config/urls.py` |
| **@action** | Custom endpoint on a ViewSet | `/applications/{id}/advance/`, `/jobs/{id}/screen/` |
| **Middleware** | Code that runs on every request/response | CORS, WhiteNoise, Security in `settings.py` |
| **Management command** | Custom `python manage.py xyz` | `seed_demo`, `screen_benchmark` |

### Likely questions

**Q: What is the N+1 query problem and how do you fix it?**
Listing 20 applications and showing each candidate's name: 1 query for applications +
20 queries for candidates = N+1. Fix with `select_related` (foreign key / one-to-one,
uses a SQL JOIN) or `prefetch_related` (many-to-many / reverse FK, uses a second query).
*In the project:* `ApplicationViewSet.get_queryset` uses `select_related("candidate", "job")`,
and `test_list_applications_uses_constant_queries` **proves** it with `django_assert_max_num_queries`.

**Q: `select_related` vs `prefetch_related`?**
`select_related` = SQL JOIN, single query, for "forward" FK/one-to-one.
`prefetch_related` = separate query then joins in Python, for many-to-many and reverse relations.

**Q: Where do you put validation?**
Field-level: `validate_<field>` in the serializer (`validate_email`). Cross-field:
`validate()` (closed job check, status transitions). Business rules that must hold no
matter where data comes from: on the model (`Application.transition_to`), and hard
guarantees in the DB (`UniqueConstraint` on candidate+job).

**Q: Explain `annotate` vs `aggregate`.**
`annotate` adds a computed value **per row** (`application_count` on each job).
`aggregate` returns **one summary** for the whole queryset (`stats` view counts per status).

**Q: How does Django handle settings across environments?**
Read from environment variables (12-factor). See `settings.py`: SQLite locally, Postgres
when `DB_NAME` is set, `DEBUG` from env, secrets from Secret Manager on GCP.

**Q: What's `auto_now` vs `auto_now_add`?** Set on every save vs only on creation.

**Q: How would you secure this API?** `IsAuthenticated` permission + Token or JWT auth
(e.g. `djangorestframework-simplejwt`), object-level permissions, throttling, HTTPS only.
(The demo uses `AllowAny`; say so and explain what you'd change.)

**Q: Function-based vs class-based views?** FBV = simple and explicit (`stats`, `health`).
CBV/ViewSets = reuse and less code for CRUD (`JobViewSet`).

---

## 2. React + Redux (Redux Toolkit)

### The data flow (draw this on a whiteboard if asked)

```
 User clicks "Advance"
        │
        ▼
 dispatch(advanceApplication(id))          ← async thunk
        │  dispatches "pending"
        ▼
 fetch POST /api/applications/5/advance/
        │
        ▼  dispatches "fulfilled" with the server's JSON
 applicationsSlice reducer → upsertOne()   ← new state (immutable, via Immer)
        │
        ▼
 selectPipelineColumns (memoized)          ← useSelector re-runs
        │
        ▼
 PipelinePage re-renders, card moves column
```

### Core concepts

| Concept | Explanation | File |
|---|---|---|
| **Store** | Single object holding all app state | `app/store.js` |
| **Slice** | Reducer + actions for one feature | `features/*/…Slice.js` |
| **Reducer** | Pure function `(state, action) → newState` | `extraReducers` in each slice |
| **Action** | Plain object `{type, payload}` describing what happened | auto-generated by RTK |
| **Thunk / createAsyncThunk** | Function for async work; dispatches pending/fulfilled/rejected | `fetchJobs`, `screenJob` |
| **Immer** | Lets you write "mutating" code that becomes an immutable update | `state.status = 'loading'` |
| **createEntityAdapter** | Normalized state `{ids, entities}` + CRUD helpers | all three slices |
| **Selector / createSelector** | Read derived data; memoized to avoid re-renders | `selectPipelineColumns` |
| **useSelector / useDispatch** | React hooks to read state / send actions | every page |
| **Provider** | Makes the store available to all components | `main.jsx` |

### Likely questions

**Q: Why Redux instead of just `useState`?** Shared state used by many components
(jobs list appears on Jobs and Pipeline pages), predictable updates, DevTools time-travel
debugging. Local UI state (form inputs) stays in `useState`. Be balanced: for small apps,
Context or React Query/RTK Query can be enough.

**Q: Why must reducers be pure / immutable?** React-Redux decides whether to re-render by
comparing references. Mutating in place means the reference doesn't change, so the UI
wouldn't update. Immer makes immutable updates easy.

**Q: Explain the three states of an async thunk.** `pending` (show loading), `fulfilled`
(save data), `rejected` (show error). See `jobsSlice.js`. `rejectWithValue` passes the
server's validation message to the UI.

**Q: What does normalizing state mean?** Store items by id (`entities[5]`) instead of
arrays, so lookups are O(1) and an update only touches one place.

**Q: How does one slice react to another slice's action?** `extraReducers`: the
applications slice listens to `screenJob.fulfilled` (from the jobs slice) to copy in scores.

**Q: What is `useEffect` dependency array?** Effect runs again only when listed values
change. `[dispatch, jobId]` in `PipelinePage` refetches when the selected job changes.

**Q: What's RTK Query?** Redux Toolkit's data-fetching/caching layer; would replace most
of the hand-written thunks. Good "next improvement" answer.

**Q: Why put the selected job in the URL?** Bookmarkable, shareable, back button works.

---

## 3. Multithreading

### The essential ideas

- **Process** = running program with its own memory. **Thread** = unit of execution inside a
  process; threads **share** memory.
- **Concurrency** = dealing with many things at once (interleaving).
  **Parallelism** = literally running at the same instant on multiple cores.
- **GIL (Global Interpreter Lock)**: in CPython only one thread executes Python bytecode at
  a time. BUT a thread waiting on I/O (network, disk, `sleep`) releases the GIL.

  **Rule of thumb:**
  - I/O-bound (API calls, DB, files, web scraping) → **threads** (`ThreadPoolExecutor`) or asyncio
  - CPU-bound (image processing, heavy math) → **processes** (`ProcessPoolExecutor`/`multiprocessing`)

### In the project: `backend/recruiting/screening.py`

```python
with ThreadPoolExecutor(max_workers=8, thread_name_prefix="screener") as pool:
    futures = {pool.submit(self._screen_one, item, progress): item["id"] for item in items}
    for future in as_completed(futures):
        try:
            results.append(future.result())
        except Exception as exc:
            results.append(ScreeningResult(app_id, error=str(exc)))
```

Talking points:
1. **Why threads work here**: the slow part is a network call (I/O-bound).
2. **Thread pool, not raw threads**: reuses a fixed number of threads, bounded resources.
3. **`as_completed`**: handle results as soon as each finishes, not in submit order.
4. **Error isolation**: one failed call doesn't crash the batch (`test_one_failure_does_not_stop_the_batch`).
5. **Race condition prevention**: `ProgressCounter` uses `threading.Lock` because `x += 1`
   is read-modify-write and not atomic. Test: `test_progress_counter_is_thread_safe`.
6. **No DB access in worker threads**: Django opens one DB connection per thread. Workers
   only do I/O and math; the main thread writes everything with **one `bulk_update`**.
7. **Measured, not assumed**: `python manage.py screen_benchmark` shows 2804 ms → 404 ms.

### Likely questions

**Q: What is a race condition?** When the result depends on the timing of threads
accessing shared data. Fix with locks, atomic operations, or by not sharing (each worker
returns its own result, as in the screener).

**Q: What is a deadlock?** Two threads each hold a lock the other needs, so both wait forever.
Avoid by always acquiring locks in the same order, using timeouts, keeping critical sections small.

**Q: How many threads should you use?** For I/O-bound work, more than CPU cores is fine,
but limited by the external API's rate limit and memory. It's configurable here
(`SCREENING_MAX_WORKERS`). Measure, don't guess.

**Q: Threads vs asyncio?** Both suit I/O. asyncio uses one thread and cooperative
`await`; needs async-compatible libraries. Threads work with normal blocking libraries
like `requests`.

**Q: Multithreading in JavaScript/React?** JS is single-threaded with an event loop;
`fetch` is async but not threaded. For heavy CPU work in the browser, use Web Workers.

**Q: Would you run a huge batch inside an HTTP request?** No. For thousands of items,
queue the job (Celery, Cloud Tasks, Pub/Sub) and let the client poll or get notified.

**Q: How do you test multithreaded code?** Inject fake dependencies (fake verifier),
assert on outcomes not timing where possible, use generous timing bounds when you must
(`test_threads_run_in_parallel_and_are_faster_than_sequential`), stress shared state with
many threads (`test_progress_counter_is_thread_safe`).

---

## 4. Selenium & QA automation

### Selenium essentials

| Concept | What to know | In project |
|---|---|---|
| **WebDriver** | API that controls a real browser | `conftest.py` `browser` fixture |
| **Locators** | `By.ID`, `CSS_SELECTOR`, `XPATH`, `NAME`, `CLASS_NAME`, `LINK_TEXT` | `tid()` in `pages/base.py` uses `data-testid` |
| **Explicit wait** | Wait until a condition is true (`WebDriverWait` + `expected_conditions`) | `BasePage.find`, `wait_for_card` |
| **Implicit wait** | Global wait for element lookup; don't mix with explicit waits | not used, on purpose |
| **Page Object Model** | One class per page; tests call methods, not locators | `e2e/pages/` |
| **Headless** | Browser without a window, for CI | `--headless=new`, `HEADED=1` to watch |
| **Fixtures** | Setup/teardown (pytest) | `browser`, `base_url`, `live_server` |
| **Screenshots on failure** | Debugging aid in CI | `pytest_runtest_makereport` hook |

### Likely questions

**Q: How do you handle flaky tests?** Root-cause first: usually timing. Replace
`time.sleep` with explicit waits on a specific condition; use stable locators
(`data-testid`, not auto-generated classes or long XPaths); isolate test data (each test
gets a fresh DB here); avoid test order dependence. Retries are a last resort and hide bugs.

**Q: Explicit vs implicit vs fluent wait?** Implicit: applies to every `find_element`.
Explicit: waits for one condition. Fluent: explicit wait with custom polling interval and
ignored exceptions. Prefer explicit.

**Q: What locator strategy do you prefer and why?** `data-testid` or IDs: stable, unique,
not tied to styling. XPath only when needed (e.g. finding by text); avoid absolute XPaths.

**Q: How do you handle `StaleElementReferenceException`?** The DOM re-rendered (very
common in React). Re-find the element instead of holding old references; wait for the new
state. The page objects re-find cards on every call for exactly this reason.

**Q: Why the Page Object Model?** Maintainability and reuse: if the Jobs form changes, you
fix `JobsPage` once, not 20 tests. Tests read like user stories.

**Q: What should be automated vs manual?** Automate: regression, smoke, data-driven,
repetitive flows, API tests. Manual/exploratory: new features in flux, usability, visual
judgement, one-off checks.

**Q: How do you test across browsers?** Selenium Grid or a cloud service
(BrowserStack/Sauce Labs) with the same tests parameterized by browser.

**Q: Selenium vs Playwright/Cypress?** Selenium: mature, all major languages and browsers,
W3C standard. Playwright/Cypress: auto-waiting, faster, nicer tooling. Know Selenium deeply
for this role; mentioning Playwright shows awareness.

### QA methodology (the "QA" half of the job title)

**The test pyramid** (and this project's numbers):
```
          /\        E2E / UI (Selenium)        9  — slow, few, critical user flows
         /  \
        /----\      Integration / API          14 — real HTTP + DB
       /      \
      /--------\    Unit                        21 (+6 Vitest) — fast, many
```

**Types of testing to define confidently**
- **Unit**: one function/class in isolation (`test_compute_match_score`)
- **Integration**: components together, e.g. API + DB (`test_api.py`)
- **Functional**: does a feature meet requirements (`test_post_a_job`)
- **Regression**: re-running tests after changes so old features don't break (the whole CI suite)
- **Smoke**: quick check that the critical path works after a deploy (`test_dashboard_shows_live_counts`, `/api/health/`)
- **Sanity**: narrow check of one fixed area after a bug fix
- **E2E**: full user journey through the real UI (`test_full_hiring_flow`)
- **Positive vs negative**: valid input works / invalid input is rejected properly
  (`test_job_form_shows_server_validation_error`, `test_duplicate_email_is_rejected`)
- **Boundary value analysis & equivalence partitioning**: test at edges (0 years, exactly
  min years) and one value per class of input; see the parametrized score tests.

**Writing a test case** (be ready to write one on the spot):

| Field | Example |
|---|---|
| ID | TC-PIPE-004 |
| Title | Applicant cannot skip pipeline stages |
| Preconditions | Application exists in status "applied" |
| Steps | 1. POST `/api/applications/{id}/status/` with `{"status":"offer"}` |
| Expected | 400 response; message "Cannot move from 'applied' to 'offer'"; status unchanged |
| Priority | High |

**Writing a bug report**: title (what + where), environment (browser, OS, build),
steps to reproduce, expected vs actual, severity/priority, screenshot/logs, and whether
it's reproducible every time.

**Severity vs priority**: severity = impact on the system; priority = how soon to fix.
(A typo on the homepage logo: low severity, high priority.)

**QA metrics** (job responsibility #10): test pass rate, defects found per release,
defect density, escaped defects (found in production), mean time to resolve, automation
coverage, flaky test rate, test execution time.

**SDLC/STLC**: requirements → test planning → test case design → environment setup →
execution → defect reporting → closure. In Agile, testing happens every sprint, and QA
joins refinement to define acceptance criteria early ("shift left").

---

## 5. Google Cloud Platform

Read `docs/GCP_DEPLOY.md` for the architecture diagram and commands.

**Q: How would you deploy a Django app on GCP?** Containerize with Docker → push to
Artifact Registry → run on **Cloud Run** (serverless containers) with **Cloud SQL**
Postgres, secrets in **Secret Manager**, CI/CD through **Cloud Build**. Alternatives:
App Engine (simpler PaaS), GKE (Kubernetes, for complex microservices), Compute Engine (VMs, full control).

**Q: Cloud Run vs App Engine vs GKE vs Compute Engine?**
- Compute Engine: virtual machines; you manage OS and everything.
- GKE: managed Kubernetes; many services, fine-grained control, more ops work.
- App Engine: PaaS; push code, Google runs it.
- Cloud Run: run any container, scales to zero, pay per use. Great default for web APIs.

**Q: How do you handle secrets?** Never in code or the image. Secret Manager, injected as
env vars (`--set-secrets` in `cloudbuild.yaml`), access controlled with IAM roles.

**Q: Where do logs go?** Anything printed to stdout/stderr in Cloud Run goes to Cloud
Logging; that's why `LOGGING` in settings writes to the console.

**Q: What's IAM?** Identity and Access Management: who (user / service account) can do
what (role) on which resource. Principle of least privilege.

**Q: How would you store uploaded files?** Cloud Storage bucket, because Cloud Run's
filesystem is temporary and not shared between instances.

**Q: How do you roll back a bad deploy?** Every Cloud Run deploy is a revision; shift 100%
of traffic back to the previous revision with one command.

**Q: Other services worth naming:** Pub/Sub (messaging), Cloud Tasks (task queue),
Cloud Scheduler (cron), BigQuery (analytics warehouse), Cloud Functions (small event-driven
code), Load Balancing, Cloud Monitoring.

---

## 6. APIs, Git and integration

**REST basics**: resources as URLs, HTTP verbs (GET read, POST create, PUT replace,
PATCH partial update, DELETE remove), stateless, status codes:
200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized (not logged in),
403 Forbidden (logged in, not allowed), 404 Not Found, 409 Conflict, 500 Server Error.

**Idempotent**: same request repeated gives same result (GET, PUT, DELETE yes; POST no).

**CORS**: browsers block JS from calling another origin unless the server allows it.
Here `django-cors-headers` allows the Vite dev server (`:5173`) to call Django (`:8000`).
In production there's no CORS because React and the API share one origin.

**Testing APIs**: Postman/Insomnia manually; pytest + `APIClient` automated (`test_api.py`).
Check status code, response body, side effects in the DB, and error cases.

**Git workflow**: feature branch → commits → push → pull request → code review → CI
passes → merge. Know: `clone, status, add, commit, push, pull, branch, checkout/switch,
merge, rebase, stash, log, diff`. Merge vs rebase: merge keeps history with a merge
commit; rebase rewrites your branch on top of main for a linear history (don't rebase
shared branches).

---

## 7. Behavioural questions (prepare a STAR story for each)

STAR = **S**ituation, **T**ask, **A**ction, **R**esult.

1. *A difficult bug you fixed.* (From client work, or here: case-insensitive duplicate
   emails slipped past DRF's unique check and caused a database error; found by a test,
   fixed in `validate_email`.)
2. *Learning a new technology quickly.* This project.
3. *Working independently / remotely.* Freelance client projects.
4. *Disagreeing with a teammate or client.*
5. *Missing a deadline or changing requirements.*

Questions to ask them:
- What does the split between development and QA work look like day to day?
- What's the current test automation coverage, and what's the biggest pain point?
- How is CI/CD set up today? Which GCP services do you use most?
- How do you measure success in the first 90 days?

---

## 8. Two-week study plan

| Days | Focus | Exercise |
|---|---|---|
| 1–2 | Run the project, read every file | Seed, click through, run all tests |
| 3–4 | Django/DRF | Add a `notes` endpoint or job closing feature + tests |
| 5–6 | React/Redux | Add a "close job" button with a thunk; install Redux DevTools and watch actions |
| 7–8 | Selenium | Write 2 new E2E tests (close job, search candidates); break a locator and fix it |
| 9 | Multithreading | Change worker count in the benchmark; remove the Lock and see the counter test fail |
| 10–11 | GCP | Deploy the cheap SQLite version to Cloud Run (free credits) |
| 12 | QA theory | Write 10 test cases + 2 bug reports for this app |
| 13–14 | Mock interview | Say the pitch out loud; answer each Q above without notes |

Deploying it and putting the live link + GitHub repo on your CV is the single most
convincing thing you can do before the interview.
