import { Page } from '../components/Page'

export function OrgSettingsPage() {
  return (
    <Page title="조직 설정" todo="1단계: 초대 코드 확인·재발급, 구성원 역할 / 계정과목·예산 등록 (총무 전용)">
      <section className="card">
        <h2 className="card__title">초대 코드</h2>
        <p className="muted">—</p>
      </section>
      <section className="card">
        <h2 className="card__title">구성원</h2>
        <p className="muted">—</p>
      </section>
      <section className="card">
        <h2 className="card__title">계정과목 · 예산</h2>
        <p className="muted">—</p>
      </section>
    </Page>
  )
}
