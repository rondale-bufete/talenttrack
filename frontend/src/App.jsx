import { NavLink, Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import JobsPage from './pages/JobsPage'
import CandidatesPage from './pages/CandidatesPage'
import PipelinePage from './pages/PipelinePage'

const links = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/jobs', label: 'Jobs' },
  { to: '/candidates', label: 'Candidates' },
  { to: '/pipeline', label: 'Pipeline' },
]

export default function App() {
  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">TalentTrack</span>
        <nav>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} data-testid={`nav-${l.label.toLowerCase()}`}>
              {l.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/jobs" element={<JobsPage />} />
          <Route path="/candidates" element={<CandidatesPage />} />
          <Route path="/pipeline" element={<PipelinePage />} />
          <Route path="*" element={<p>Page not found.</p>} />
        </Routes>
      </main>
    </div>
  )
}
