import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, Vite serves the app on :5173 and forwards /api to Django on :8000.
// In production, Django serves the built files from /static/, so the build uses that base.
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'build' ? '/static/' : '/',
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
  test: { environment: 'node' },
}))
