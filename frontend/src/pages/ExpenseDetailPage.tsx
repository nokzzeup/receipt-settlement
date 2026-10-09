import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { useCategories } from '../api/categories'
import { errorMessage } from '../api/client'
import { useExpense } from '../api/expenses'
import type { Category, ExpenseDetail } from '../api/types'
import { ExpenseForm } from '../components/ExpenseForm'
import { Icon } from '../components/Icon'
import { OcrText } from '../components/OcrText'
import { Page } from '../components/Page'
import { ReceiptThumb } from '../components/ReceiptImage'
import { SkeletonRows } from '../components/SkeletonRows'
import { StatusBadge } from '../components/StatusBadge'
import { SubmitDone } from '../components/SubmitDone'
import { TopBar } from '../components/TopBar'
import { useOrgId } from '../hooks/useOrgId'
import { categoryLook, chipStyle } from '../lib/categoryStyle'
import { formatDateTime, formatWon } from '../lib/format'
import { stagger } from '../lib/motion'

/** 지출 상세. 작성 중이고 내가 고칠 수 있으면 확인·수정 폼, 아니면 읽기 전용 */
export function ExpenseDetailPage() {
  const orgId = useOrgId()
  const expenseId = Number(useParams().expenseId)
  const expense = useExpense(orgId, expenseId)
  const categories = useCategories(orgId)
  // 방금 제출한 지출 → 완료 화면 (제출하면 폼이 읽기 전용으로 바뀌므로 페이지가 들고 있음)
  const [submitted, setSubmitted] = useState<ExpenseDetail | null>(null)
  const listUrl = `/orgs/${orgId}/expenses`

  if (expense.isPending) {
    return (
      <>
        <TopBar back={listUrl} title="지출" />
        <div className="screen">
          <div className="card card--list">
            <SkeletonRows count={3} />
          </div>
        </div>
      </>
    )
  }
  if (expense.isError) {
    return (
      <Page title="지출을 열 수 없어요" subtitle={errorMessage(expense.error)}>
        <Link className="btn btn--secondary btn--block" to={listUrl}>
          지출 목록으로
        </Link>
      </Page>
    )
  }

  const data = expense.data
  return (
    <>
      <TopBar back={listUrl} backLabel="지출 목록으로" title={data.can_edit ? '내용 확인' : '지출 상세'} />
      <div className={data.can_edit ? 'screen screen--with-cta' : 'screen'}>
        {data.can_edit ? (
          <ExpenseForm key={data.id} orgId={orgId} expense={data} onSubmitted={setSubmitted} />
        ) : (
          <ExpenseReadOnly orgId={orgId} expense={data} categories={categories.data} />
        )}
      </div>
      {submitted && (
        <SubmitDone orgId={orgId} expense={submitted} categories={categories.data} onClose={() => setSubmitted(null)} />
      )}
    </>
  )
}

type ReadOnlyProps = { orgId: number; expense: ExpenseDetail; categories: Category[] | undefined }

function ExpenseReadOnly({ orgId, expense, categories }: ReadOnlyProps) {
  const { receipt } = expense
  const categoryOf = (id: number | null) => categories?.find((c) => c.id === id)

  return (
    <>
      <div className="anim-rise" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, padding: '0 4px' }}>
        <StatusBadge status={expense.status} reimbursed={expense.reimbursed_at !== null} />
        <span className="caption">
          {expense.uploader.name} · {formatDateTime(expense.created_at)} 등록
        </span>
      </div>

      {expense.status === 'DRAFT' && (
        <p className="banner banner--warn anim-rise">
          <Icon name="info" size={20} />
          작성 중인 지출이에요. 올린 사람이나 총무만 고칠 수 있어요
        </p>
      )}
      {expense.status === 'REJECTED' && expense.reject_reason && (
        <p className="banner banner--danger anim-rise">
          <Icon name="alert" size={20} />
          반려 사유: {expense.reject_reason}
        </p>
      )}

      <section className="card receipt-fields anim-rise" style={stagger(1)} aria-label="영수증 정보">
        <ReceiptThumb orgId={orgId} expenseId={expense.id} />
        <dl className="receipt-fields__inputs">
          <div className="field">
            <dt className="field__label">가게</dt>
            <dd style={{ fontSize: 17, fontWeight: 600 }}>{receipt.store_name ?? '—'}</dd>
          </div>
          <div className="field">
            <dt className="field__label">결제일시</dt>
            <dd style={{ fontSize: 16 }}>{formatDateTime(receipt.paid_at) || '—'}</dd>
          </div>
        </dl>
      </section>

      <section className="card anim-rise" style={stagger(2)} aria-label="청구 금액">
        <p className="field__label">청구 금액</p>
        <p className="big-number" style={{ fontSize: 28, marginTop: 4 }}>
          {formatWon(expense.amount)}
        </p>
        <p className="caption" style={{ marginTop: 4 }}>
          영수증 합계 {receipt.total_amount != null ? formatWon(receipt.total_amount) : '—'}
        </p>
        <div className="payer-row">
          <span>결제한 사람 (돌려받을 사람)</span>
          <span style={{ color: 'var(--text)', fontWeight: 600 }}>{expense.payer.name}</span>
        </div>
      </section>

      <section className="card card--list anim-rise" style={{ ...stagger(3), paddingInline: 16 }} aria-label="품목">
        <div className="card__head" style={{ padding: '0 4px' }}>
          <h2 className="card__title">품목 {expense.items.length}개</h2>
        </div>
        <div style={{ marginTop: 4 }}>
          {expense.items.map((item) => {
            const category = categoryOf(item.category_id)
            const look = categoryLook(category)
            return (
              <div key={item.id} className="item-card">
                <div className="item-card__readonly">
                  <span className="row-item__main">
                    <span className="row-item__title">{item.name}</span>
                    <span className="row-item__sub">
                      {item.quantity}개{item.unit_price != null && ` × ${formatWon(item.unit_price)}`}
                    </span>
                  </span>
                  <span className="amount" style={{ fontSize: 16 }}>
                    {formatWon(item.amount)}
                  </span>
                </div>
                <span className="cat-chip" style={{ ...chipStyle(look), alignSelf: 'flex-start' }}>
                  <span className="cat-chip__icon" style={{ color: look.fg }}>
                    <Icon name={look.icon} size={16} />
                  </span>
                  {category?.name ?? '미분류'}
                  {item.category_source === 'AUTO' && <span className="auto-badge">자동</span>}
                </span>
              </div>
            )
          })}
        </div>
      </section>

      <OcrText lines={receipt.ocr_text} />
    </>
  )
}
