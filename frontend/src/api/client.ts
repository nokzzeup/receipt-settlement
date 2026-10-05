import createClient, { type Middleware } from 'openapi-fetch'
import { clearToken, getToken } from '../auth/token'
import type { paths } from './schema'

/**
 * 타입이 붙은 API 클라이언트. 경로·요청·응답 타입은 src/api/schema.d.ts(자동 생성)에서 온다.
 *
 *   const data = unwrap(await api.GET('/api/v1/auth/me'))
 *
 * 백엔드 API가 바뀌면: 백엔드 실행 중인 상태에서 `npm run gen:api`
 */
export const api = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? '',
})

const auth: Middleware = {
  onRequest({ request }) {
    const token = getToken()
    if (token) request.headers.set('Authorization', `Bearer ${token}`)
    return request
  },
  onResponse({ request, response }) {
    // 토큰 만료·무효 → 토큰 지우고 로그인 화면으로 (로그인 시도 자체의 401은 화면에서 메시지로 처리)
    if (response.status === 401 && getToken() && !request.url.includes('/auth/login')) {
      clearToken()
      window.location.assign('/login')
    }
    return response
  },
}
api.use(auth)

/** 2xx가 아닌 응답 */
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

/** openapi-fetch 결과에서 data를 꺼낸다. 실패면 ApiError를 던져서 TanStack Query의 error로 넘어가게 */
export function unwrap<T>(result: { data?: T; error?: unknown; response: Response }): T {
  if (result.response.ok) return result.data as T
  throw new ApiError(result.response.status, result.error)
}

/** 에러를 화면에 보여줄 한국어 문장으로 */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const detail = (error.body as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string') return detail // 서버가 보낸 한국어 메시지
    if (error.status === 422) return '입력한 값을 다시 확인하세요.'
    return `요청을 처리하지 못했습니다. (HTTP ${error.status})`
  }
  return '서버에 연결할 수 없습니다. 백엔드가 켜져 있는지 확인하세요.'
}
