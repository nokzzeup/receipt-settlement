import { STATUS_LABELS, type ExpenseStatus } from '../api/types'

/** 지출 상태 배지. 환급까지 끝난 승인 건은 '환급 완료' */
export function StatusBadge({ status, reimbursed = false }: { status: ExpenseStatus; reimbursed?: boolean }) {
  const modifier = reimbursed ? 'reimbursed' : status.toLowerCase()
  return <span className={`pill pill--${modifier}`}>{reimbursed ? '환급 완료' : STATUS_LABELS[status]}</span>
}
