import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  createCandidate, fetchCandidates, selectAllCandidates,
} from '../features/candidates/candidatesSlice'
import { parseSkills } from '../api/client'

const EMPTY = { full_name: '', email: '', skills: '', years_experience: 0 }

export default function CandidatesPage() {
  const dispatch = useDispatch()
  const candidates = useSelector(selectAllCandidates)
  const { createError } = useSelector((s) => s.candidates)
  const [form, setForm] = useState(EMPTY)
  const [query, setQuery] = useState('')

  useEffect(() => {
    dispatch(fetchCandidates())
  }, [dispatch])

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const onSubmit = async (e) => {
    e.preventDefault()
    const result = await dispatch(createCandidate({
      full_name: form.full_name,
      email: form.email,
      skills: parseSkills(form.skills),
      years_experience: Number(form.years_experience) || 0,
    }))
    if (createCandidate.fulfilled.match(result)) setForm(EMPTY)
  }

  // Derived data: computed during render, never stored in state
  const q = query.trim().toLowerCase()
  const visible = q
    ? candidates.filter((c) => c.full_name.toLowerCase().includes(q) || c.skills.includes(q))
    : candidates

  return (
    <section>
      <h1>Candidates</h1>

      <form className="card form" onSubmit={onSubmit} data-testid="candidate-form">
        <h2>Add a candidate</h2>
        <div className="grid2">
          <label>Full name<input name="full_name" value={form.full_name} onChange={onChange} data-testid="cand-name" /></label>
          <label>Email<input name="email" type="email" value={form.email} onChange={onChange} data-testid="cand-email" /></label>
          <label>Skills (comma-separated)<input name="skills" value={form.skills} onChange={onChange} data-testid="cand-skills" /></label>
          <label>Years experience
            <input name="years_experience" type="number" min="0" value={form.years_experience} onChange={onChange} data-testid="cand-years" />
          </label>
        </div>
        {createError && <p className="error" data-testid="cand-form-error">{createError}</p>}
        <button type="submit" data-testid="cand-submit">Add candidate</button>
      </form>

      <input
        className="search"
        placeholder="Filter by name or skill…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        data-testid="cand-filter"
      />

      <table className="table" data-testid="candidate-table">
        <thead><tr><th>Name</th><th>Email</th><th>Skills</th><th>Years</th></tr></thead>
        <tbody>
          {visible.map((c) => (
            <tr key={c.id} data-testid="candidate-row">
              <td>{c.full_name}</td>
              <td>{c.email}</td>
              <td>{c.skills.join(', ')}</td>
              <td>{c.years_experience}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
