import { useHealth } from '../api/health'

/** 개발 모드에서만 보이는 백엔드 연결 표시줄 (빌드 결과물에는 안 나옴) */
export function ApiStatus() {
  const { data, isPending, isError } = useHealth()

  let state: 'pending' | 'ok' | 'error' = 'pending'
  let label = '확인 중…'
  if (isError) {
    state = 'error'
    label = '연결 실패 — 터미널의 [api] 로그를 확인하세요'
  } else if (data) {
    state = data.database === 'ok' ? 'ok' : 'error'
    label = `API ok · DB ${data.database}`
  } else if (!isPending) {
    state = 'error'
    label = '응답 없음'
  }

  return (
    <div className={`api-status api-status--${state}`} role="status">
      DEV · 백엔드: {label}
    </div>
  )
}
