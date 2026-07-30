import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// API prefixes owned by the FastAPI app. "/" and "/static" stay unproxied
// (they're the legacy Jinja home page); "/mcp" is backend-to-backend only.
const API_PREFIXES = ['/auth', '/users', '/expenses', '/oauth', '/.well-known']

export default defineConfig(() => {
  const target = process.env.VITE_PROXY_TARGET ?? 'http://localhost:8000'

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': '/src',
      },
    },
    server: {
      port: 5173,
      proxy: Object.fromEntries(
        API_PREFIXES.map((prefix) => [prefix, { target, changeOrigin: true }]),
      ),
    },
  }
})
