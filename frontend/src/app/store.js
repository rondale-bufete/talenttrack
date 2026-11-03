import { configureStore } from '@reduxjs/toolkit'
import jobsReducer from '../features/jobs/jobsSlice'
import candidatesReducer from '../features/candidates/candidatesSlice'
import applicationsReducer from '../features/applications/applicationsSlice'
import statsReducer from '../features/stats/statsSlice'

// configureStore adds redux-thunk and Redux DevTools support automatically.
export const makeStore = (preloadedState) =>
  configureStore({
    reducer: {
      jobs: jobsReducer,
      candidates: candidatesReducer,
      applications: applicationsReducer,
      stats: statsReducer,
    },
    preloadedState,
  })

export const store = makeStore()
