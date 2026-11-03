import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import { createJob, fetchJobs, screenJob, selectAllJobs } from '../features/jobs/jobsSlice'
import { parseSkills } from '../api/client'

const EMPTY = { title: '', department: '', skills: '', min_years_experience: 0 }

export default function JobsPage() {
  const dispatch = useDispatch()
  const jobs = useSelector(selectAllJobs)
  const { status, createError, screening } = useSelector((s) => s.jobs)
  const [form, setForm] = useState(EMPTY)

  useEffect(() => {
    dispatch(fetchJobs())
  }, [dispatch])

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const onSubmit = async (e) => {
    e.preventDefault()
    const result = await dispatch(createJob({
      title: form.title,
      department: form.department,
      required_skills: parseSkills(form.skills),
      min_years_experience: Number(form.min_years_experience) || 0,
    }))
    if (createJob.fulfilled.match(result)) setForm(EMPTY)
  }

  return (
    <section>
      <h1>Jobs</h1>

      <form className="card form" onSubmit={onSubmit} data-testid="job-form">
        <h2>Post a job</h2>
        <div className="grid2">
          <label>Title<input name="title" value={form.title} onChange={onChange} data-testid="job-title" /></label>
          <label>Department<input name="department" value={form.department} onChange={onChange} data-testid="job-department" /></label>
          <label>Required skills (comma-separated)
            <input name="skills" value={form.skills} onChange={onChange} placeholder="django, react, selenium" data-testid="job-skills" />
          </label>
          <label>Min. years experience
            <input name="min_years_experience" type="number" min="0" value={form.min_years_experience} onChange={onChange} data-testid="job-min-years" />
          </label>
        </div>
        {createError && <p className="error" data-testid="job-form-error">{createError}</p>}
        <button type="submit" data-testid="job-submit">Post job</button>
      </form>

      {status === 'loading' && <p className="muted">Loading jobs…</p>}
      {status === 'succeeded' && jobs.length === 0 && <p className="muted">No jobs yet.</p>}

      <ul className="list" data-testid="job-list">
        {jobs.map((job) => {
          const run = screening[job.id]
          return (
            <li key={job.id} className="card" data-testid="job-row">
              <div className="row-head">
                <div>
                  <strong data-testid="job-row-title">{job.title}</strong>
                  <span className="muted"> · {job.department || 'General'} · {job.application_count} applicants</span>
                </div>
                <div className="actions">
                  <Link to={`/pipeline?job=${job.id}`} className="btn-link">Pipeline</Link>
                  <button
                    onClick={() => dispatch(screenJob(job.id))}
                    disabled={run?.status === 'loading'}
                    data-testid="screen-button"
                  >
                    {run?.status === 'loading' ? 'Screening…' : 'Run screening'}
                  </button>
                </div>
              </div>
              <div className="chips">
                {job.required_skills.map((s) => <span key={s} className="chip">{s}</span>)}
              </div>
              {run?.status === 'succeeded' && (
                <p className="ok" data-testid="screen-result">
                  Screened {run.report.screened} applicants in {run.report.elapsed_ms} ms
                  using {run.report.workers} threads
                  {run.report.failed > 0 && ` (${run.report.failed} failed)`}.
                </p>
              )}
              {run?.status === 'failed' && <p className="error">{run.error}</p>}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
