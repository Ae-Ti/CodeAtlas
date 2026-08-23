import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // dev 중 /api 요청을 백엔드로 프록시한다.
    // 주의: 프록시를 거쳐도 브라우저의 Origin 헤더(http://localhost:<이 서버 포트>)는 그대로
    // 백엔드에 전달되므로, 백엔드 CORS 허용 목록(application.yml codeatlas.cors)에 이 포트가
    // 들어 있어야 POST 가 403 으로 막히지 않는다. 기본값은 localhost 전 포트 허용.
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET ?? 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
})
