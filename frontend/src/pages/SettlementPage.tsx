import { Page } from '../components/Page'

export function SettlementPage() {
  return (
    <Page title="정산 현황" todo="5단계: 결제자별 환급 대상 금액, 환급 완료 처리, 계정별 집행액·잔액, 예산 초과 경고">
      <section className="card">
        <h2 className="card__title">환급 대기</h2>
        <p className="muted">—</p>
      </section>
      <section className="card">
        <h2 className="card__title">계정별 예산</h2>
        <p className="muted">—</p>
      </section>
    </Page>
  )
}
