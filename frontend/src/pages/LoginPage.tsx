import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'
import { useLogin, useSignup } from '../api/auth'
import { errorMessage } from '../api/client'
import { getToken } from '../auth/token'
import { Page } from '../components/Page'

type Mode = 'login' | 'signup'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from ?? '/orgs'

  const [mode, setMode] = useState<Mode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  const login = useLogin()
  const signup = useSignup()
  const pending = login.isPending || signup.isPending
  const serverError = mode === 'login' ? login.error : signup.error

  if (getToken()) return <Navigate to="/orgs" replace />

  function switchMode(next: Mode) {
    setMode(next)
    setFormError(null)
    login.reset()
    signup.reset()
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setFormError(null)
    if (mode === 'login') {
      // 로그인: 원래 가려던 화면으로 복귀
      login.mutate({ email, password }, { onSuccess: () => navigate(from, { replace: true }) })
      return
    }
    if (!name.trim()) return setFormError('이름을 입력하세요.')
    if (password.length < 8) return setFormError('비밀번호는 8자 이상이어야 합니다.')
    // 새 계정은 아직 소속 조직이 없으므로 항상 조직 선택 화면으로
    signup.mutate({ email, password, name }, { onSuccess: () => navigate('/orgs', { replace: true }) })
  }

  return (
    <Page title={mode === 'login' ? '로그인' : '회원가입'}>
      <div className="tabs" role="tablist">
        <button type="button" role="tab" aria-selected={mode === 'login'} className="tabs__item" onClick={() => switchMode('login')}>
          로그인
        </button>
        <button type="button" role="tab" aria-selected={mode === 'signup'} className="tabs__item" onClick={() => switchMode('signup')}>
          회원가입
        </button>
      </div>

      <form className="stack" onSubmit={handleSubmit}>
        {mode === 'signup' && (
          <input className="input" placeholder="이름" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" required />
        )}
        <input
          className="input"
          type="email"
          placeholder="이메일"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          required
        />
        <input
          className="input"
          type="password"
          placeholder={mode === 'signup' ? '비밀번호 (8자 이상)' : '비밀번호'}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
          required
        />
        {(formError || serverError) && <p className="error">{formError ?? errorMessage(serverError)}</p>}
        <button className="button button--primary" type="submit" disabled={pending}>
          {pending ? '처리 중…' : mode === 'login' ? '로그인' : '가입하고 시작하기'}
        </button>
      </form>
    </Page>
  )
}
