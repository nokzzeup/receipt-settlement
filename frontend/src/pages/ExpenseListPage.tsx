import { Link } from 'react-router'
import { Page } from '../components/Page'

export function ExpenseListPage() {
  return (
    <Page title="지출 목록" todo="2단계: 지출 목록 API 연결 (상태별: 작성 중 / 제출 / 승인 / 반려)">
      <p className="muted">아직 등록된 지출이 없습니다.</p>
      <Link className="button" to="../receipts/new" relative="path">
        영수증 촬영하기
      </Link>
    </Page>
  )
}
