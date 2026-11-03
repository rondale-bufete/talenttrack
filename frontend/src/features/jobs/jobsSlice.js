import { createAsyncThunk, createEntityAdapter, createSlice } from '@reduxjs/toolkit'
import { api } from '../../api/client'

/*
 * createEntityAdapter stores items "normalized": { ids: [3, 1], entities: {1: {...}, 3: {...}} }
 * Looking one up by id is O(1) and updates never duplicate rows.
 */
const jobsAdapter = createEntityAdapter()

// createAsyncThunk dispatches 3 actions for us: pending -> fulfilled | rejected
export const fetchJobs = createAsyncThunk('jobs/fetchAll', async () => {
  const data = await api.listJobs()
  return data.results
})

export const createJob = createAsyncThunk('jobs/create', async (job, { rejectWithValue }) => {
  try {
    return await api.createJob(job)
  } catch (err) {
    return rejectWithValue(err.message) // shows the server's validation message in the UI
  }
})

export const screenJob = createAsyncThunk('jobs/screen', async (jobId, { rejectWithValue }) => {
  try {
    return await api.screenJob(jobId)
  } catch (err) {
    return rejectWithValue(err.message)
  }
})

const jobsSlice = createSlice({
  name: 'jobs',
  initialState: jobsAdapter.getInitialState({
    status: 'idle', // idle | loading | succeeded | failed
    error: null,
    createError: null,
    screening: {}, // { [jobId]: { status, report, error } }
  }),
  reducers: {
    clearCreateError(state) {
      state.createError = null
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchJobs.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(fetchJobs.fulfilled, (state, action) => {
        state.status = 'succeeded'
        jobsAdapter.setAll(state, action.payload)
      })
      .addCase(fetchJobs.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.error.message
      })
      .addCase(createJob.pending, (state) => {
        state.createError = null
      })
      .addCase(createJob.fulfilled, (state, action) => {
        // Redux Toolkit uses Immer, so this "mutation" is actually an immutable update
        jobsAdapter.addOne(state, { application_count: 0, ...action.payload })
      })
      .addCase(createJob.rejected, (state, action) => {
        state.createError = action.payload ?? action.error.message
      })
      .addCase(screenJob.pending, (state, action) => {
        state.screening[action.meta.arg] = { status: 'loading', report: null, error: null }
      })
      .addCase(screenJob.fulfilled, (state, action) => {
        state.screening[action.meta.arg] = { status: 'succeeded', report: action.payload, error: null }
      })
      .addCase(screenJob.rejected, (state, action) => {
        state.screening[action.meta.arg] = { status: 'failed', report: null, error: action.payload }
      })
  },
})

export const { clearCreateError } = jobsSlice.actions
export default jobsSlice.reducer

export const {
  selectAll: selectAllJobs,
  selectById: selectJobById,
} = jobsAdapter.getSelectors((state) => state.jobs)
