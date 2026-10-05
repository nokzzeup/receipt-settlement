// 로그인 토큰 보관 (브라우저 localStorage). 막혀 있는 환경(사생활 보호 모드 등)에서도 앱이 죽지 않게 try/catch
const KEY = 'receipt-settlement.token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}

export function setToken(token: string) {
  try {
    localStorage.setItem(KEY, token)
  } catch {
    // 저장 못 하면 새로고침 시 다시 로그인해야 할 뿐
  }
}

export function clearToken() {
  try {
    localStorage.removeItem(KEY)
  } catch {
    // 무시
  }
}
