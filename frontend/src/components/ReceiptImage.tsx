import { useState } from 'react'
import { useReceiptImage } from '../api/expenses'

/** 영수증 원본 사진. 누르면 크게 보기 ↔ 접기 */
export function ReceiptImage({ orgId, expenseId }: { orgId: number; expenseId: number }) {
  const image = useReceiptImage(orgId, expenseId)
  const [expanded, setExpanded] = useState(false)

  if (image.isError) return <p className="muted">원본 사진을 불러오지 못했어요.</p>
  if (!image.data) return <div className="receipt-image receipt-image--loading">사진 불러오는 중…</div>

  return (
    <button
      type="button"
      className={expanded ? 'receipt-image receipt-image--expanded' : 'receipt-image'}
      onClick={() => setExpanded((v) => !v)}
      aria-label={expanded ? '사진 접기' : '사진 크게 보기'}
    >
      <img src={image.data.url} alt="영수증 원본" />
    </button>
  )
}
