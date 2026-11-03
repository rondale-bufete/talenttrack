import { createAsyncThunk, createEntityAdapter, createSlice } from '@reduxjs/toolkit'
import { api } from '../../api/client'

const candidatesAdapter = createEntityAdapter({
  sortComparer: (a, b) => a.full_name.localeCompare(b.full_name),
})

export const fetchCandidates = createAsyncThunk('candidates/fetchAll', async () => {
  const data = await api.listCandidates()
  return data.results
})

export const createCandidate = createAsyncThunk(
  'candidates/create',
  async (candidate, { rejectWithValue }) => {
    try {
      return await api.createCandidate(candidate)
    } catch (err) {
      return rejectWithValue(err.message)
    }
  },
)

const candidatesSlice = createSlice({
  name: 'candidates',
  initialState: candidatesAdapter.getInitialState({ status: 'idle', error: null, createError: null }),
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchCandidates.pending, (state) => {
        state.status = 'loading'
      })
      .addCase(fetchCandidates.fulfilled, (state, action) => {
        state.status = 'succeeded'
        candidatesAdapter.setAll(state, action.payload)
      })
      .addCase(fetchCandidates.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.error.message
      })
      .addCase(createCandidate.pending, (state) => {
        state.createError = null
      })
      .addCase(createCandidate.fulfilled, (state, action) => {
        candidatesAdapter.addOne(state, action.payload)
      })
      .addCase(createCandidate.rejected, (state, action) => {
        state.createError = action.payload ?? action.error.message
      })
  },
})

export default candidatesSlice.reducer

export const { selectAll: selectAllCandidates } = candidatesAdapter.getSelectors(
  (state) => state.candidates,
)
