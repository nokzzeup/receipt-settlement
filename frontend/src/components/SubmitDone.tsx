import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router'
import type { Category, ExpenseDetail } from '../api/types'
import { categoryLook } from '../lib/categoryStyle'
import { formatWon } from '../lib/format'

type Props = {
  orgId: number
  expense: ExpenseDetail
  categories: Category[] | undefined
  onClose: () => void
}

/** 제출 완료 화면: 체크 표시가 그려지고, 계정과목별 금액 막대가 차오른다 (품목 단위 분리) */
export function SubmitDone({ orgId, expense, categories, onClose }: Props) {
  const [grown, setGrown] = useState(false)
  useEffect(() => {
    const id = window.setTimeout(() => setGrown(true), 900)
    return () => window.clearTimeout(id)
  }, [])

  const byCategory = new Map<number | null, number>()
  for (const item of expense.items) byCategory.set(item.category_id, (byCategory.get(item.category_id) ?? 0) + item.amount)
  const total = Math.max(1, [...byCategory.values()].reduce((a, b) => a + Math.max(0, b), 0))
  const split = [...byCategory.entries()]
    .filter(([, amount]) => amount > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([id, amount]) => {
      const category = categories?.find((c) => c.id === id)
      return { id, name: category?.name ?? '미분류', amount, color: categoryLook(category).fg }
    })

  return createPortal(
    <div className="done-screen" role="dialog" aria-modal="true" aria-labelledby="submit-done-title">
      <div className="done-screen__body">
        <svg className="done-screen__check" width="92" height="92" viewBox="0 0 92 92" aria-hidden="true">
          <circle cx="46" cy="46" r="40" fill="none" stroke="var(--primary)" strokeWidth="5" />
          <path
            d="M29 47.5 41 59.5 63.5 34.5"
            fill="none"
            stroke="var(--primary)"
            strokeWidth="6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <h2 id="submit-done-title" className="anim-rise" style={{ animationDelay: '0.55s' }}>
          제출했어요
        </h2>
        <p className="anim-rise" style={{ animationDelay: '0.62s' }}>
          승인되면 정산 대상에 들어가요
        </p>
        <div className="split anim-rise" style={{ animationDelay: '0.72s' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12 }}>
            <span style={{ fontSize: 15, fontWeight: 600 }}>{expense.receipt.store_name ?? '가게 이름 없음'}</span>
            <span className="amount" style={{ fontSize: 17 }}>
              {formatWon(expense.amount)}
            </span>
          </div>
          <div className="split__bar" aria-hidden="true">
            {split.map((part, i) => (
              <span
                key={part.id ?? 'none'}
                style={{
                  width: grown ? `${(part.amount / total) * 100}%` : '0%',
                  background: part.color,
                  transitionDelay: `${i * 120}ms`,
                }}
              />
            ))}
          </div>
          <ul className="split__legend">
            {split.map((part) => (
              <li key={part.id ?? 'none'}>
                <span className="split__dot" style={{ background: part.color }} />
                <span style={{ flex: 1, color: 'var(--text-2)' }}>{part.name}</span>
                <span className="amount" style={{ fontWeight: 600 }}>
                  {formatWon(part.amount)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
      <div className="anim-rise" style={{ animationDelay: '0.85s', display: 'flex', flexDirection: 'column', gap: 6 }}>
        <Link className="btn btn--primary btn--block" to={`/orgs/${orgId}`}>
          홈으로
        </Link>
        <button type="button" className="btn btn--text btn--block" onClick={onClose}>
          제출한 내용 보기
        </button>
      </div>
    </div>,
    document.body,
  )
}
