import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'
import { useLogin, useSignup } from '../api/auth'
import { errorMessage } from '../api/client'
import { getToken } from '../auth/token'
import { Icon } from '../components/Icon'
import { SegmentedTabs } from '../components/SegmentedTabs'
import { stagger } from '../lib/motion'

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
  const message = formError ?? (serverError ? errorMessage(serverError) : null)

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
    <div className="auth">
      <div className="auth__brand anim-rise">
        <span className="auth__logo anim-pop">
          <Icon name="receipt" size={30} weight={2} />
        </span>
        <h1>
          영수증 찍으면
          <br />
          정산까지 한 번에
        </h1>
        <p>법인카드 없는 학생회·동아리를 위한 지출 정산</p>
      </div>

      <div className="anim-rise" style={stagger(1)}>
        <SegmentedTabs
          label="로그인 또는 회원가입"
          segments={[
            { key: 'login', label: '로그인' },
            { key: 'signup', label: '회원가입' },
          ]}
          value={mode}
          onChange={switchMode}
        />
      </div>

      <form className="form-stack anim-rise" style={stagger(2)} onSubmit={handleSubmit}>
        {mode === 'signup' && (
          <input
            className="input anim-fade"
            placeholder="이름"
            aria-label="이름"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="name"
            required
          />
        )}
        <input
          className="input"
          type="email"
          placeholder="이메일"
          aria-label="이메일"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="email"
          required
        />
        <input
          className="input"
          type="password"
          placeholder={mode === 'signup' ? '비밀번호 (8자 이상)' : '비밀번호'}
          aria-label="비밀번호"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
          required
        />
        {message && (
          <p key={message} className="message message--error anim-rise" role="alert">
            <Icon name="alert" size={18} />
            {message}
          </p>
        )}
        <button className="btn btn--primary btn--block" type="submit" disabled={pending} style={{ marginTop: 6 }}>
          {pending ? '처리 중…' : mode === 'login' ? '로그인' : '가입하고 시작하기'}
        </button>
      </form>
    </div>
  )
}
