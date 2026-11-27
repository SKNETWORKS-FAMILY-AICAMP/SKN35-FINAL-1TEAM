import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())

  return {
    plugins: [react(), tailwindcss()],
    server: {
      // 같은 출처로 요청해야 refresh 쿠키(HttpOnly)가 함께 전달된다
      proxy: {
        '/api': env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
      },
    },
  }
})
