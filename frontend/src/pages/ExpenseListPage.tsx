import { Link } from 'react-router'
import { errorMessage } from '../api/client'
import { useExpenses } from '../api/expenses'
import { Page } from '../components/Page'
import { StatusBadge } from '../components/StatusBadge'
import { useOrgId } from '../hooks/useOrgId'
import { formatDate, formatWon } from '../lib/format'

/** 지출 목록 (총무·승인자: 조직 전체 / 구성원: 내가 올렸거나 내가 결제자인 것) */
export function ExpenseListPage() {
  const orgId = useOrgId()
  const expenses = useExpenses(orgId)

  return (
    <Page title="지출 목록">
      <Link className="button button--primary" to={`/orgs/${orgId}/receipts/new`}>
        + 영수증 촬영하기
      </Link>

      {expenses.isPending && <p className="muted">불러오는 중…</p>}
      {expenses.isError && <p className="error">{errorMessage(expenses.error)}</p>}
      {expenses.data?.length === 0 && <p className="muted">아직 등록된 지출이 없어요. 영수증을 찍어서 시작하세요.</p>}
      {expenses.data && expenses.data.length > 0 && (
        <ul className="list">
          {expenses.data.map((e) => (
            <li key={e.id}>
              <Link className="list__item list__link" to={String(e.id)}>
                <span className="list__main">
                  {e.store_name ?? '가게명 미입력'}
                  <span className="list__sub">
                    {formatDate(e.paid_at ?? e.created_at)} · {e.payer.name} · 품목 {e.item_count}개
                    {e.status === 'DRAFT' && e.uncategorized_count > 0 && ` · 미분류 ${e.uncategorized_count}`}
                  </span>
                </span>
                <span className="list__end">
                  <span className="amount">{formatWon(e.amount)}</span>
                  <StatusBadge status={e.status} reimbursed={e.reimbursed_at !== null} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Page>
  )
}
