import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('@mui') || id.includes('@emotion')) return 'mui'
          if (id.includes('@tanstack') || id.includes('axios')) return 'data'
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './tests/setup.js',
    css: true,
    testTimeout: 15000,
  },
})
