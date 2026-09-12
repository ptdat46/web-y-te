import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Proxy API requests so cookies work same-origin (SameSite=Lax)
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Proxy WebSocket connections to Django Channels
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
