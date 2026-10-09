import type { CSSProperties } from 'react'
import { Link } from 'react-router'
import type { Category, ExpenseSummary } from '../api/types'
import { formatShortDay, formatWon } from '../lib/format'
import { CategoryTile } from './CategoryTile'
import { StatusBadge } from './StatusBadge'

type Props = {
  orgId: number
  expense: ExpenseSummary
  categories: Category[] | undefined
  /** 아래 줄 앞에 날짜를 붙일지 (날짜별로 묶은 목록에서는 끔) */
  showDay?: boolean
  style?: CSSProperties
  className?: string
}

/** 지출 한 줄: 계정 아이콘 · 가게 이름 · 결제자/품목 수 · 금액 · 상태 */
export function ExpenseRow({ orgId, expense: e, categories, showDay = false, style, className }: Props) {
  const category = categories?.find((c) => c.id === e.main_category_id)
  const parts = [
    showDay ? formatShortDay(e.paid_at ?? e.created_at) : null,
    `결제 ${e.payer.name}`,
    `품목 ${e.item_count}개`,
  ].filter(Boolean)
  const needsCategory = e.status === 'DRAFT' && e.uncategorized_count > 0

  return (
    <Link
      to={`/orgs/${orgId}/expenses/${e.id}`}
      className={className ? `row-item press ${className}` : 'row-item press'}
      style={style}
    >
      <CategoryTile category={category} />
      <span className="row-item__main">
        <span className="row-item__title">{e.store_name ?? '가게 이름 없음'}</span>
        <span className="row-item__sub">
          {parts.join(' · ')}
          {needsCategory && <span style={{ color: 'var(--warn)' }}> · 미분류 {e.uncategorized_count}</span>}
        </span>
      </span>
      <span className="row-item__end">
        <span className="amount">{formatWon(e.amount)}</span>
        <StatusBadge status={e.status} reimbursed={e.reimbursed_at !== null} />
      </span>
    </Link>
  )
}
