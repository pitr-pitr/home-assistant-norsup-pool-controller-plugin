import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

const apiProxy = process.env.LOOM_API_PROXY || 'http://127.0.0.1:8001'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@loom/whats-new': path.resolve(__dirname, '../.loom/whats-new'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/v1': apiProxy,
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
