import {
  createAsyncThunk, createEntityAdapter, createSelector, createSlice,
} from '@reduxjs/toolkit'
import { api } from '../../api/client'
import { screenJob } from '../jobs/jobsSlice'

export const PIPELINE = ['applied', 'screening', 'interview', 'offer', 'hired', 'rejected']

const applicationsAdapter = createEntityAdapter()

export const fetchApplications = createAsyncThunk('applications/fetchForJob', async (jobId) => {
  const data = await api.listApplications(jobId)
  return data.results
})

export const applyToJob = createAsyncThunk(
  'applications/create',
  async ({ candidate, job }, { rejectWithValue }) => {
    try {
      return await api.createApplication({ candidate, job })
    } catch (err) {
      return rejectWithValue(err.message)
    }
  },
)

export const advanceApplication = createAsyncThunk(
  'applications/advance',
  async (id, { rejectWithValue }) => {
    try {
      return await api.advanceApplication(id)
    } catch (err) {
      return rejectWithValue(err.message)
    }
  },
)

export const rejectApplication = createAsyncThunk(
  'applications/reject',
  async (id, { rejectWithValue }) => {
    try {
      return await api.setApplicationStatus(id, 'rejected')
    } catch (err) {
      return rejectWithValue(err.message)
    }
  },
)

const applicationsSlice = createSlice({
  name: 'applications',
  initialState: applicationsAdapter.getInitialState({ status: 'idle', error: null }),
  reducers: {
    clearApplicationError(state) {
      state.error = null
    },
  },
  extraReducers: (builder) => {
    const saveOne = (state, action) => {
      state.error = null
      applicationsAdapter.upsertOne(state, action.payload)
    }
    const fail = (state, action) => {
      state.error = action.payload ?? action.error.message
    }
    builder
      .addCase(fetchApplications.pending, (state) => {
        state.status = 'loading'
      })
      .addCase(fetchApplications.fulfilled, (state, action) => {
        state.status = 'succeeded'
        applicationsAdapter.setAll(state, action.payload)
      })
      .addCase(fetchApplications.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.error.message
      })
      .addCase(applyToJob.fulfilled, saveOne)
      .addCase(applyToJob.rejected, fail)
      .addCase(advanceApplication.fulfilled, saveOne)
      .addCase(advanceApplication.rejected, fail)
      .addCase(rejectApplication.fulfilled, saveOne)
      .addCase(rejectApplication.rejected, fail)
      // Cross-slice reaction: when screening finishes, copy the new scores in.
      .addCase(screenJob.fulfilled, (state, action) => {
        const updates = action.payload.results
          .filter((r) => !r.error && state.entities[r.application_id])
          .map((r) => ({
            id: r.application_id,
            changes: { match_score: r.match_score, skills_verified: r.skills_verified },
          }))
        applicationsAdapter.updateMany(state, updates)
      })
  },
})

export const { clearApplicationError } = applicationsSlice.actions
export default applicationsSlice.reducer

export const { selectAll: selectAllApplications } = applicationsAdapter.getSelectors(
  (state) => state.applications,
)

/*
 * Memoized selector (reselect): groups applications into pipeline columns.
 * It only recomputes when the applications array changes, so components
 * don't re-render on unrelated state updates.
 */
export const selectPipelineColumns = createSelector([selectAllApplications], (apps) => {
  const columns = Object.fromEntries(PIPELINE.map((s) => [s, []]))
  for (const app of apps) columns[app.status]?.push(app)
  for (const s of PIPELINE) {
    columns[s].sort((a, b) => (b.match_score ?? -1) - (a.match_score ?? -1))
  }
  return columns
})
