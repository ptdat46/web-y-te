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
        target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
      // Proxy WebSocket connections to Django Channels
      '/ws': {
        target: process.env.VITE_WS_PROXY_TARGET || 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
