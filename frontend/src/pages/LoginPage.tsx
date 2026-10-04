import { Link } from 'react-router'
import { Page } from '../components/Page'

export function LoginPage() {
  return (
    <Page title="로그인" todo="1단계: 이메일/비밀번호 로그인 + JWT, 회원가입">
      <form className="stack" onSubmit={(e) => e.preventDefault()}>
        <input className="input" type="email" placeholder="이메일" autoComplete="email" />
        <input className="input" type="password" placeholder="비밀번호" autoComplete="current-password" />
        <button className="button" type="submit" disabled>
          로그인
        </button>
      </form>
      <p className="muted">
        <Link to="/orgs">(개발용) 로그인 없이 조직 선택으로 →</Link>
      </p>
    </Page>
  )
}
