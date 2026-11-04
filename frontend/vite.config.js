import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, Vite serves the app on :5173 and forwards /api to Django.
// Locally Django runs on 127.0.0.1:8000; in Docker it's the backend-dev container.
// In production, Django serves the built files from /static/, so the build uses that base.
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'build' ? '/static/' : '/',
  server: {
    proxy: { '/api': process.env.VITE_API_TARGET || 'http://127.0.0.1:8000' },
    watch: { usePolling: process.env.VITE_USE_POLLING === 'true' },
  },
  test: { environment: 'node' },
}))
