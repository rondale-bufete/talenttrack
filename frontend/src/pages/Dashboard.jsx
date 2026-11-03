import { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { fetchStats } from '../features/stats/statsSlice'
import { PIPELINE } from '../features/applications/applicationsSlice'

export default function Dashboard() {
  const dispatch = useDispatch()
  const { data, status, error } = useSelector((s) => s.stats)

  // Refresh every time the dashboard opens
  useEffect(() => {
    dispatch(fetchStats())
  }, [dispatch])

  if (status === 'failed') return <p className="error">Could not load stats: {error}</p>
  if (!data) return <p className="muted">Loading…</p>

  const max = Math.max(1, ...Object.values(data.by_status))

  return (
    <section>
      <h1>Dashboard</h1>
      <div className="stat-grid">
        <Stat label="Open jobs" value={data.open_jobs} id="open-jobs" />
        <Stat label="Candidates" value={data.candidates} id="candidates" />
        <Stat label="Applications" value={data.applications} id="applications" />
        <Stat label="Hired" value={data.by_status.hired} id="hired" />
      </div>

      <h2>Applications by stage</h2>
      <div className="bars">
        {PIPELINE.map((s) => (
          <div className="bar-row" key={s}>
            <span className="bar-label">{s}</span>
            <div className="bar-track">
              <div className={`bar-fill st-${s}`} style={{ width: `${(data.by_status[s] / max) * 100}%` }} />
            </div>
            <span className="bar-value">{data.by_status[s]}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

function Stat({ label, value, id }) {
  return (
    <div className="stat">
      <div className="stat-value" data-testid={`stat-${id}`}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}
