import createClient from 'openapi-fetch'
import type { paths } from './schema'

/**
 * 타입이 붙은 API 클라이언트. 경로·요청·응답 타입은 src/api/schema.d.ts(자동 생성)에서 온다.
 *
 *   const { data, error, response } = await api.GET('/api/v1/health')
 *
 * 백엔드 API가 바뀌면: 백엔드 실행 중인 상태에서 `npm run gen:api`
 */
export const api = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? '',
})

// 1단계(인증): 여기서 api.use({ onRequest }) 미들웨어로 Authorization 헤더를 붙인다

/** 2xx가 아닌 응답을 TanStack Query 에러로 넘길 때 사용 */
export class ApiError extends Error {
  readonly status: number
  readonly body: unknown

  constructor(status: number, body: unknown) {
    super(`API 요청 실패 (HTTP ${status})`)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}
