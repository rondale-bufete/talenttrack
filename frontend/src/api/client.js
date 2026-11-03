// One small wrapper around fetch so every request handles JSON and errors the same way.
const BASE = '/api'

export class ApiError extends Error {
  constructor(status, body) {
    super(ApiError.describe(body) || `Request failed (${status})`)
    this.status = status
    this.body = body
  }

  // DRF errors look like {"email": ["already exists"]} or {"detail": "..."}
  static describe(body) {
    if (!body || typeof body !== 'object') return ''
    if (body.detail) return body.detail
    return Object.entries(body)
      .map(([field, msgs]) => `${field}: ${[].concat(msgs).join(' ')}`)
      .join(' · ')
  }
}

export async function request(path, { method = 'GET', body } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = res.status === 204 ? null : await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, data)
  return data
}

export const api = {
  listJobs: () => request('/jobs/?page_size=200'),
  createJob: (job) => request('/jobs/', { method: 'POST', body: job }),
  screenJob: (id) => request(`/jobs/${id}/screen/`, { method: 'POST' }),

  listCandidates: () => request('/candidates/?page_size=200'),
  createCandidate: (c) => request('/candidates/', { method: 'POST', body: c }),

  listApplications: (jobId) => request(`/applications/?page_size=200&job=${jobId}`),
  createApplication: (a) => request('/applications/', { method: 'POST', body: a }),
  advanceApplication: (id) => request(`/applications/${id}/advance/`, { method: 'POST' }),
  setApplicationStatus: (id, status) =>
    request(`/applications/${id}/status/`, { method: 'POST', body: { status } }),

  stats: () => request('/stats/'),
}

// Turns "Django, react ,  Selenium" into ["Django", "react", "Selenium"]
export const parseSkills = (text) =>
  text.split(',').map((s) => s.trim()).filter(Boolean)
