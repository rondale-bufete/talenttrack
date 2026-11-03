import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useSearchParams } from 'react-router-dom'
import { fetchJobs, screenJob, selectAllJobs } from '../features/jobs/jobsSlice'
import { fetchCandidates, selectAllCandidates } from '../features/candidates/candidatesSlice'
import {
  PIPELINE, advanceApplication, applyToJob, clearApplicationError, fetchApplications,
  rejectApplication, selectPipelineColumns,
} from '../features/applications/applicationsSlice'

export default function PipelinePage() {
  const dispatch = useDispatch()
  const [params, setParams] = useSearchParams()
  const jobs = useSelector(selectAllJobs)
  const candidates = useSelector(selectAllCandidates)
  const columns = useSelector(selectPipelineColumns)
  const { error } = useSelector((s) => s.applications)
  const [candidateId, setCandidateId] = useState('')

  // The selected job lives in the URL (?job=3) so the page can be bookmarked/shared
  const jobId = params.get('job') || (jobs[0] && String(jobs[0].id)) || ''

  useEffect(() => {
    dispatch(fetchJobs())
    dispatch(fetchCandidates())
  }, [dispatch])

  useEffect(() => {
    if (jobId) dispatch(fetchApplications(jobId))
  }, [dispatch, jobId])

  const applied = new Set(Object.values(columns).flat().map((a) => a.candidate))
  const available = candidates.filter((c) => !applied.has(c.id))

  const onApply = async (e) => {
    e.preventDefault()
    if (!candidateId) return
    await dispatch(applyToJob({ candidate: Number(candidateId), job: Number(jobId) }))
    setCandidateId('')
  }

  return (
    <section>
      <h1>Pipeline</h1>

      <div className="toolbar">
        <label>Job
          <select
            value={jobId}
            onChange={(e) => {
              dispatch(clearApplicationError())
              setParams({ job: e.target.value })
            }}
            data-testid="pipeline-job"
          >
            {jobs.map((j) => <option key={j.id} value={j.id}>{j.title}</option>)}
          </select>
        </label>

        <form onSubmit={onApply} className="inline">
          <select value={candidateId} onChange={(e) => setCandidateId(e.target.value)} data-testid="apply-candidate">
            <option value="">Add an applicant…</option>
            {available.map((c) => <option key={c.id} value={c.id}>{c.full_name}</option>)}
          </select>
          <button type="submit" disabled={!candidateId} data-testid="apply-submit">Add</button>
        </form>

        <button onClick={() => dispatch(screenJob(Number(jobId)))} disabled={!jobId} data-testid="pipeline-screen">
          Score applicants
        </button>
      </div>

      {error && <p className="error" data-testid="pipeline-error">{error}</p>}

      <div className="board">
        {PIPELINE.map((stage) => (
          <div key={stage} className="column" data-testid={`column-${stage}`}>
            <h3>{stage} <span className="count">{columns[stage].length}</span></h3>
            {columns[stage].map((app) => (
              <div key={app.id} className="app-card" data-testid="app-card" data-app-id={app.id}>
                <div className="app-name">{app.candidate_name}</div>
                <div className="muted small">
                  Score:{' '}
                  <span data-testid="app-score">{app.match_score ?? '—'}</span>
                  {app.skills_verified === true && ' · verified'}
                </div>
                {!['hired', 'rejected'].includes(stage) && (
                  <div className="card-actions">
                    <button onClick={() => dispatch(advanceApplication(app.id))} data-testid="advance">Advance</button>
                    <button className="ghost" onClick={() => dispatch(rejectApplication(app.id))} data-testid="reject">Reject</button>
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>
    </section>
  )
}
