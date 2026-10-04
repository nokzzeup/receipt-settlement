import { useParams } from 'react-router'
import { Page } from '../components/Page'

/** OCR 인식 결과 확인·수정 (ReceiptFields 형태로 받아서 사용자가 고친 뒤 지출로 등록) */
export function ReceiptReviewPage() {
  const { receiptId } = useParams()

  return (
    <Page
      title="인식 결과 확인"
      todo={`2단계: 영수증 #${receiptId} 인식 결과(가게명·결제일시·합계·품목) 수정 폼 → 지출 등록`}
    >
      <dl className="fields">
        <dt>가게명</dt>
        <dd>—</dd>
        <dt>결제일시</dt>
        <dd>—</dd>
        <dt>합계</dt>
        <dd>—</dd>
      </dl>
      <p className="muted">품목: 이름 · 수량 · 단가 · 금액 · 계정과목</p>
    </Page>
  )
}
