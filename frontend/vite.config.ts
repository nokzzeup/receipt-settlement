import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

// .env는 레포 루트에 하나만 두고 백엔드와 같이 쓴다 (브라우저에는 VITE_ 접두사 값만 노출됨)
const envDir = fileURLToPath(new URL('..', import.meta.url))

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, envDir, '')

  return {
    envDir,
    plugins: [
      react(),
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
        manifest: {
          name: '영수증 정산',
          short_name: '정산',
          description: '법인카드 없는 조직을 위한 영수증 기반 지출 정산',
          lang: 'ko',
          theme_color: '#0f766e',
          background_color: '#ffffff',
          display: 'standalone',
          start_url: '/',
          icons: [
            { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
            { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
            { src: 'pwa-maskable-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
          ],
        },
        workbox: {
          // API 요청·문서는 앱 셸(index.html)로 대체하지 않음
          navigateFallbackDenylist: [/^\/api\//, /^\/docs/, /^\/openapi\.json/],
        },
      }),
    ],
    server: {
      port: 5173,
      strictPort: true, // 5173이 이미 쓰이면 다른 포트로 몰래 바꾸지 말고 에러 → 주소가 항상 같음
      strictPort: true, // 5173이 이미 쓰이면 다른 포트로 몰래 바꾸지 말고 에러 (주소가 항상 같게)
      // /api 요청을 백엔드로 넘김 → 같은 출처라 CORS 불필요, 폰에서 접속해도 그대로 동작
      proxy: {
        '/api': {
          target: env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  }
})
