import { Link, useSearchParams } from 'react-router'
import { useCategories } from '../api/categories'
import { errorMessage } from '../api/client'
import { useExpenses } from '../api/expenses'
import type { ExpenseStatus, ExpenseSummary } from '../api/types'
import { ExpenseRow } from '../components/ExpenseRow'
import { Icon } from '../components/Icon'
import { LargeTitle } from '../components/Page'
import { SegmentedTabs } from '../components/SegmentedTabs'
import { SkeletonRows } from '../components/SkeletonRows'
import { useOrgId } from '../hooks/useOrgId'
import { formatDayLabel, formatWon, seoulDayKey } from '../lib/format'
import { stagger } from '../lib/motion'

type FilterKey = 'ALL' | ExpenseStatus

const FILTERS: { key: FilterKey; label: string }[] = [
  { key: 'ALL', label: '전체' },
  { key: 'DRAFT', label: '작성 중' },
  { key: 'SUBMITTED', label: '대기' },
  { key: 'APPROVED', label: '승인' }, // 환급 완료도 승인된 지출
  { key: 'REJECTED', label: '반려' },
]

const isFilterKey = (value: string | null): value is FilterKey => FILTERS.some((f) => f.key === value)
const matches = (filter: FilterKey) => (e: ExpenseSummary) => filter === 'ALL' || e.status === filter
const dayOf = (e: ExpenseSummary) => e.paid_at ?? e.created_at

type Group = { key: string; label: string; items: ExpenseSummary[] }

/** 결제일(없으면 등록일) 기준 한국 날짜별로 묶기. 최근 날짜가 위로 */
function groupByDay(list: ExpenseSummary[]): Group[] {
  const sorted = [...list].sort((a, b) => dayOf(b).localeCompare(dayOf(a)) || b.id - a.id)
  const groups: Group[] = []
  for (const e of sorted) {
    const key = seoulDayKey(dayOf(e))
    const last = groups.at(-1)
    if (last?.key === key) last.items.push(e)
    else groups.push({ key, label: formatDayLabel(dayOf(e)), items: [e] })
  }
  return groups
}

/** 지출 목록 (총무·승인자: 조직 전체 / 구성원: 내가 올렸거나 내가 결제자인 것). 상태별로 거르기 */
export function ExpenseListPage() {
  const orgId = useOrgId()
  const expenses = useExpenses(orgId)
  const categories = useCategories(orgId)
  const [params, setParams] = useSearchParams()
  const filterParam = params.get('filter')
  const filter: FilterKey = isFilterKey(filterParam) ? filterParam : 'ALL'

  const all = expenses.data ?? []
  const visible = all.filter(matches(filter))
  const groups = groupByDay(visible)
  const total = visible.reduce((sum, e) => sum + e.amount, 0)
  const filterLabel = FILTERS.find((f) => f.key === filter)?.label

  function changeFilter(key: FilterKey) {
    setParams(key === 'ALL' ? {} : { filter: key }, { replace: true })
  }

  return (
    <>
      <div className="topbar-spacer" aria-hidden="true" />
      <div className="screen screen--with-tabbar">
        <LargeTitle
          title="지출"
          subtitle={expenses.data ? `${visible.length}건 · ${formatWon(total)}` : '불러오는 중…'}
        />

        <div className="anim-rise" style={stagger(1)}>
          <SegmentedTabs
            label="지출 상태로 거르기"
            segments={FILTERS.map((f) => ({ ...f, count: all.filter(matches(f.key)).length }))}
            value={filter}
            onChange={changeFilter}
          />
        </div>

        {expenses.isPending && (
          <div className="card card--list">
            <SkeletonRows count={4} />
          </div>
        )}
        {expenses.isError && <p className="banner banner--danger">{errorMessage(expenses.error)}</p>}

        {expenses.data && all.length === 0 && (
          <div className="card anim-rise" style={stagger(2)}>
            <div className="empty">
              <span className="empty__icon">
                <Icon name="receipt" />
              </span>
              <p className="empty__title">아직 등록된 지출이 없어요</p>
              <p className="empty__desc">결제하고 받은 영수증을 찍어서 시작하세요</p>
              <Link className="btn btn--primary btn--md" style={{ marginTop: 10 }} to={`/orgs/${orgId}/receipts/new`}>
                <Icon name="camera" size={20} />
                영수증 찍기
              </Link>
            </div>
          </div>
        )}
        {expenses.data && all.length > 0 && visible.length === 0 && (
          <div className="card anim-fade">
            <div className="empty">
              <p className="empty__title">'{filterLabel}' 지출이 없어요</p>
            </div>
          </div>
        )}

        {/* 거르기를 바꾸면 목록을 새로 그려서 다시 순서대로 떠오르게 */}
        <div key={filter} style={{ display: 'flex', flexDirection: 'column' }}>
          {groups.map((group, index) => (
            <section
              key={group.key}
              className="anim-rise"
              style={stagger(Math.min(index, 6) + 2)}
              aria-label={group.label}
            >
              <h2 className="group-label">{group.label}</h2>
              <div className="card" style={{ padding: '4px 10px' }}>
                {group.items.map((e) => (
                  <ExpenseRow key={e.id} orgId={orgId} expense={e} categories={categories.data} />
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </>
  )
}
