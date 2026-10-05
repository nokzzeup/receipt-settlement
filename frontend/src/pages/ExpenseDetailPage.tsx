import { Link, useParams } from 'react-router'
import { useCategories } from '../api/categories'
import { errorMessage } from '../api/client'
import { useExpense } from '../api/expenses'
import type { ExpenseDetail } from '../api/types'
import { ExpenseForm } from '../components/ExpenseForm'
import { Page } from '../components/Page'
import { ReceiptImage } from '../components/ReceiptImage'
import { StatusBadge } from '../components/StatusBadge'
import { useOrgId } from '../hooks/useOrgId'
import { formatDateTime, formatWon } from '../lib/format'

/** 지출 상세. 작성 중이고 내가 고칠 수 있으면 확인·수정 폼, 아니면 읽기 전용 */
export function ExpenseDetailPage() {
  const orgId = useOrgId()
  const expenseId = Number(useParams().expenseId)
  const expense = useExpense(orgId, expenseId)

  if (expense.isPending) {
    return (
      <Page title="지출">
        <p className="muted">불러오는 중…</p>
      </Page>
    )
  }
  if (expense.isError) {
    return (
      <Page title="지출을 열 수 없어요">
        <p className="muted">{errorMessage(expense.error)}</p>
        <Link to={`/orgs/${orgId}/expenses`}>← 지출 목록으로</Link>
      </Page>
    )
  }

  const data = expense.data
  return (
    <Page title={data.can_edit ? '인식 결과 확인·수정' : '지출 상세'}>
      <div className="row row--between">
        <StatusBadge status={data.status} reimbursed={data.reimbursed_at !== null} />
        <span className="muted">
          {data.uploader.name} · {formatDateTime(data.created_at)} 등록
        </span>
      </div>
      <ReceiptImage orgId={orgId} expenseId={data.id} />
      {data.can_edit ? (
        <ExpenseForm key={data.id} orgId={orgId} expense={data} />
      ) : (
        <ExpenseReadOnly orgId={orgId} expense={data} />
      )}
      <OcrText lines={data.receipt.ocr_text} />
    </Page>
  )
}

function ExpenseReadOnly({ orgId, expense }: { orgId: number; expense: ExpenseDetail }) {
  const categories = useCategories(orgId)
  const categoryName = (id: number | null) =>
    id === null ? '미분류' : (categories.data?.find((c) => c.id === id)?.name ?? '…')
  const { receipt } = expense

  return (
    <div className="stack">
      {expense.status === 'DRAFT' && <p className="notice">작성 중인 지출이에요. 영수증을 올린 사람이나 총무만 고칠 수 있어요.</p>}
      {expense.status === 'REJECTED' && expense.reject_reason && (
        <p className="notice notice--warn">반려 사유: {expense.reject_reason}</p>
      )}
      <section className="card">
        <dl className="fields">
          <dt>가게명</dt>
          <dd>{receipt.store_name ?? '—'}</dd>
          <dt>결제일시</dt>
          <dd>{formatDateTime(receipt.paid_at) || '—'}</dd>
          <dt>영수증 합계</dt>
          <dd>{receipt.total_amount != null ? formatWon(receipt.total_amount) : '—'}</dd>
          <dt>결제자</dt>
          <dd>{expense.payer.name}</dd>
          <dt>청구 금액</dt>
          <dd className="summary__strong">{formatWon(expense.amount)}</dd>
        </dl>
      </section>
      <section className="card">
        <h2 className="card__title">품목 {expense.items.length}개</h2>
        <ul className="list">
          {expense.items.map((item) => (
            <li key={item.id} className="list__item">
              <span className="list__main">
                {item.name}
                <span className="list__sub">
                  {categoryName(item.category_id)} · {item.quantity}개
                  {item.unit_price != null && ` × ${formatWon(item.unit_price)}`}
                </span>
              </span>
              <span className="amount">{formatWon(item.amount)}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

function OcrText({ lines }: { lines: string[] }) {
  if (lines.length === 0) return null
  return (
    <details className="ocr-text">
      <summary>인식된 원문 보기 ({lines.length}줄)</summary>
      <pre>{lines.join('\n')}</pre>
    </details>
  )
}
