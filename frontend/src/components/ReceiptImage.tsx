import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { useReceiptImage } from '../api/expenses'
import { Icon } from './Icon'

/** 영수증 원본 사진 작은 썸네일. 누르면 화면 가득 크게 (다시 누르거나 Esc로 닫기) */
export function ReceiptThumb({ orgId, expenseId }: { orgId: number; expenseId: number }) {
  const image = useReceiptImage(orgId, expenseId)
  const [zoomed, setZoomed] = useState(false)

  useEffect(() => {
    if (!zoomed) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setZoomed(false)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [zoomed])

  if (image.isError) {
    return (
      <span className="receipt-thumb" title="원본 사진을 불러오지 못했어요">
        <Icon name="image" style={{ color: 'var(--icon)' }} />
      </span>
    )
  }
  if (!image.data) return <span className="receipt-thumb skeleton" aria-label="사진 불러오는 중" />

  return (
    <>
      <button type="button" className="receipt-thumb press" onClick={() => setZoomed(true)} aria-label="영수증 사진 크게 보기">
        <img src={image.data.url} alt="" />
        <span className="receipt-thumb__zoom" aria-hidden="true">
          <Icon name="zoom" size={14} weight={2.2} />
        </span>
      </button>
      {zoomed &&
        createPortal(
          <button type="button" className="zoom" onClick={() => setZoomed(false)} aria-label="크게 보기 닫기">
            <img src={image.data.url} alt="영수증 원본" />
          </button>,
          document.body,
        )}
    </>
  )
}
