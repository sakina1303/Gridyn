import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: process.env.GITHUB_PAGES === 'true' ? '/Gridyn/' : '/',
  server: {
    proxy: { '/v1': 'http://127.0.0.1:8765' },
  },
})
