// Reducers are pure functions, so they're easy to unit test without a browser.
import { describe, expect, it } from 'vitest'
import reducer, {
  advanceApplication, fetchApplications, selectPipelineColumns,
} from './applicationsSlice'
import { screenJob } from '../jobs/jobsSlice'

const app = (id, status, score = null) => ({ id, status, match_score: score, candidate: id })

describe('applications reducer', () => {
  it('stores fetched applications normalized by id', () => {
    const state = reducer(undefined, fetchApplications.fulfilled([app(1, 'applied'), app(2, 'offer')], '', 1))
    expect(state.ids).toEqual([1, 2])
    expect(state.entities[2].status).toBe('offer')
    expect(state.status).toBe('succeeded')
  })

  it('replaces an application after it is advanced', () => {
    let state = reducer(undefined, fetchApplications.fulfilled([app(1, 'applied')], '', 1))
    state = reducer(state, advanceApplication.fulfilled(app(1, 'screening'), '', 1))
    expect(state.entities[1].status).toBe('screening')
    expect(state.ids).toHaveLength(1)
  })

  it('records the server error when advancing fails', () => {
    const state = reducer(undefined, advanceApplication.rejected(null, '', 1, 'status: cannot advance'))
    expect(state.error).toBe('status: cannot advance')
  })

  it('copies screening scores into matching applications', () => {
    let state = reducer(undefined, fetchApplications.fulfilled([app(1, 'applied')], '', 1))
    const report = { results: [{ application_id: 1, match_score: 85, skills_verified: true, error: null }] }
    state = reducer(state, screenJob.fulfilled(report, '', 1))
    expect(state.entities[1].match_score).toBe(85)
  })
})

describe('selectPipelineColumns', () => {
  it('groups by status and sorts by score, best first', () => {
    const applications = reducer(
      undefined,
      fetchApplications.fulfilled([app(1, 'applied', 40), app(2, 'applied', 90), app(3, 'hired', 70)], '', 1),
    )
    const cols = selectPipelineColumns({ applications })
    expect(cols.applied.map((a) => a.id)).toEqual([2, 1])
    expect(cols.hired).toHaveLength(1)
    expect(cols.rejected).toEqual([])
  })

  it('is memoized: same input returns the same object', () => {
    const applications = reducer(undefined, fetchApplications.fulfilled([app(1, 'applied')], '', 1))
    const state = { applications }
    expect(selectPipelineColumns(state)).toBe(selectPipelineColumns(state))
  })
})
