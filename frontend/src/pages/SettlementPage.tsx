import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { errorMessage } from '../api/client'
import { useOrg, useUpdateOrg } from '../api/orgs'
import { useBulkReimburse, useSettlement } from '../api/settlement'
import type { CategoryUsage, PayerBalance, Settlement } from '../api/types'
import { BottomSheet } from '../components/BottomSheet'
import { BudgetMeter } from '../components/BudgetMeter'
import { CategoryTile } from '../components/CategoryTile'
import { Icon } from '../components/Icon'
import { LargeTitle } from '../components/Page'
import { SegmentedTabs } from '../components/SegmentedTabs'
import { SkeletonRows } from '../components/SkeletonRows'
import { useFeedback } from '../feedback/context'
import { useCountUp } from '../hooks/useCountUp'
import { useOrgId } from '../hooks/useOrgId'
import { currentSemester, formatNumber, formatPeriod, formatShortDay, formatWon, seoulToday } from '../lib/format'
import { stagger } from '../lib/motion'

type Tab = 'payers' | 'budget'

const initialOf = (name: string) => name.trim().slice(0, 1) || '?'

/** 정산: 결제한 사람별 돌려줄 돈('보냈어요') + 계정별 예산 사용 (계산은 서버 정산 엔진) */
export function SettlementPage() {
  const orgId = useOrgId()
  const org = useOrg(orgId)
  const settlement = useSettlement(orgId)
  const [params, setParams] = useSearchParams()
  const tab: Tab = params.get('tab') === 'budget' ? 'budget' : 'payers'
  const isTreasurer = org.data?.my_role === 'TREASURER'
  const data = settlement.data

  return (
    <>
      <div className="topbar-spacer" aria-hidden="true" />
      <div className="screen screen--with-tabbar">
        <LargeTitle
          title="정산"
          subtitle={tab === 'payers' ? '승인된 지출을 결제한 사람에게 돌려줘요' : '계정과목별로 얼마 썼고 얼마 남았는지 봐요'}
        />
        <div className="anim-rise" style={stagger(1)}>
          <SegmentedTabs
            label="정산 보기"
            segments={[
              { key: 'payers', label: '돌려줄 돈' },
              { key: 'budget', label: '예산' },
            ]}
            value={tab}
            onChange={(key) => setParams(key === 'budget' ? { tab: 'budget' } : {}, { replace: true })}
          />
        </div>

        {settlement.isPending && (
          <section className="card card--list">
            <SkeletonRows count={3} />
          </section>
        )}
        {settlement.isError && <p className="message message--error">{errorMessage(settlement.error)}</p>}
        {data &&
          (tab === 'payers' ? (
            <PayersView key="payers" orgId={orgId} data={data} isTreasurer={isTreasurer} />
          ) : (
            <BudgetView key="budget" orgId={orgId} data={data} isTreasurer={isTreasurer} />
          ))}
      </div>
    </>
  )
}

// ---------- 돌려줄 돈 ----------

function PayersView({ orgId, data, isTreasurer }: { orgId: number; data: Settlement; isTreasurer: boolean }) {
  const total = useCountUp(data.to_reimburse)
  const reimburse = useBulkReimburse(orgId)
  const { toast, confirm } = useFeedback()
  // 연 시점의 내용을 들고 있음: 보낸 뒤 목록에서 사라져도 닫히는 동안 내용이 남게, '보냈어요'는 본 목록 그대로 보내게
  const [sheet, setSheet] = useState<{ payer: PayerBalance; open: boolean } | null>(null)
  const isOrg = data.scope === 'org'

  async function sendAll(payer: PayerBalance) {
    const name = payer.payer.name
    const ok = await confirm({
      title: `${name}님에게 ${formatWon(payer.to_reimburse)} 보냈나요?`,
      message: `지출 ${payer.expenses.length}건을 모두 환급 완료로 표시해요.\n송금은 각자 은행 앱으로 해주세요`,
      confirmLabel: '보냈어요',
    })
    if (!ok) return
    try {
      await reimburse.mutateAsync({ payerId: payer.payer.membership_id, expenseIds: payer.expenses.map((e) => e.id) })
      setSheet((s) => (s ? { ...s, open: false } : s))
      toast(`${name}님에게 보낸 걸로 표시했어요`)
    } catch (error) {
      setSheet((s) => (s ? { ...s, open: false } : s))
      toast(errorMessage(error))
    }
  }

  return (
    <>
      <section className="card anim-rise" style={stagger(2)} aria-label="돌려줄 돈 합계">
        <p style={{ color: 'var(--text-2)', fontSize: 15, fontWeight: 600 }}>{isOrg ? '돌려줘야 할 돈' : '내가 돌려받을 돈'}</p>
        <p className="big-number" style={{ marginTop: 8 }}>
          {formatNumber(total)}원
        </p>
        <div className="pill-row" style={{ marginTop: 14 }}>
          {data.to_reimburse_count > 0 ? (
            <span className="pill pill--lg pill--primary">승인된 지출 {data.to_reimburse_count}건</span>
          ) : (
            <span className="caption">지금 돌려줄 돈이 없어요</span>
          )}
          {data.awaiting_count > 0 && (
            <span className="pill pill--lg pill--warn">
              승인 대기 {data.awaiting_count}건 · {formatWon(data.awaiting_approval)}
            </span>
          )}
        </div>
        {isOrg && data.awaiting_count > 0 && (
          <Link className="card__footer-link" to={`/orgs/${orgId}/expenses?filter=SUBMITTED`} style={{ marginTop: 10 }}>
            승인 기다리는 지출 보기
            <Icon name="chevronRight" size={18} />
          </Link>
        )}
      </section>

      <section className="card card--list anim-rise" style={stagger(3)} aria-label={isOrg ? '사람별' : '내 지출'}>
        <div className="card__head">
          <h2 className="card__title">{isOrg ? '사람별' : '내 몫'}</h2>
        </div>
        <div className="rows" style={{ marginTop: 6 }}>
          {data.payers.length === 0 && (
            <div className="empty">
              <span className="empty__icon" style={{ background: 'var(--primary-weak)', color: 'var(--primary)' }}>
                <Icon name="wallet" />
              </span>
              <p className="empty__title">돌려줄 돈이 없어요</p>
              <p className="empty__desc">지출이 승인되면 결제한 사람별로 여기 모여요</p>
            </div>
          )}
          {data.payers.map((p) => (
            <button
              key={p.payer.membership_id}
              type="button"
              className="row-item press"
              onClick={() => setSheet({ payer: p, open: true })}
              aria-label={`${p.payer.name} ${formatWon(p.to_reimburse)} 자세히`}
            >
              <span className="tile tile--md tile--round" style={{ fontSize: 15 }}>
                {initialOf(p.payer.name)}
              </span>
              <span className="row-item__main">
                <span className="row-item__title">{p.payer.name}</span>
                <span className="row-item__sub">
                  {[
                    p.expenses.length > 0 && `지출 ${p.expenses.length}건`,
                    p.awaiting_count > 0 && `승인 대기 ${p.awaiting_count}건 · ${formatWon(p.awaiting_approval)}`,
                  ]
                    .filter(Boolean)
                    .join(' · ')}
                </span>
              </span>
              <span className="row-item__end">
                <span className="amount" style={p.to_reimburse === 0 ? { color: 'var(--text-3)' } : undefined}>
                  {formatWon(p.to_reimburse)}
                </span>
              </span>
              <Icon name="chevronRight" size={20} className="row-item__chevron" />
            </button>
          ))}
        </div>
        <p className="caption" style={{ padding: '8px 8px 12px', lineHeight: 1.6 }}>
          {isTreasurer
            ? "송금은 각자 은행 앱으로 하고, 보낸 뒤 사람을 눌러 '보냈어요'로 표시해요"
            : '총무가 보내고 표시하면 환급 완료로 바뀌어요'}
        </p>
      </section>

      <BottomSheet
        open={sheet?.open ?? false}
        onClose={() => setSheet((s) => (s ? { ...s, open: false } : s))}
        onExited={() => setSheet(null)}
        title={sheet ? `${sheet.payer.payer.name}님에게 돌려줄 돈` : ''}
        description={sheet ? `${formatWon(sheet.payer.to_reimburse)} · 승인된 지출 ${sheet.payer.expenses.length}건` : undefined}
      >
        {sheet && (
          <>
            <div className="rows sheet__body">
              {sheet.payer.expenses.map((e) => (
                <Link key={e.id} to={`/orgs/${orgId}/expenses/${e.id}`} className="row-item press">
                  <span className="tile tile--md" style={{ background: 'var(--surface-2)', color: 'var(--text-2)' }}>
                    <Icon name="receipt" size={20} />
                  </span>
                  <span className="row-item__main">
                    <span className="row-item__title">{e.store_name ?? '가게 이름 없음'}</span>
                    <span className="row-item__sub">{e.paid_at ? formatShortDay(e.paid_at) : '결제일 모름'}</span>
                  </span>
                  <span className="amount">{formatWon(e.amount)}</span>
                </Link>
              ))}
              {sheet.payer.expenses.length === 0 && (
                <p className="caption" style={{ padding: 8 }}>
                  아직 승인된 지출이 없어요
                  {sheet.payer.awaiting_count > 0 && ` · 승인 대기 ${sheet.payer.awaiting_count}건`}
                </p>
              )}
            </div>
            {isTreasurer && sheet.payer.expenses.length > 0 && (
              <div className="sheet__actions">
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={() => sendAll(sheet.payer)}
                  disabled={reimburse.isPending || !sheet.open}
                >
                  <Icon name="send" size={20} />
                  {formatWon(sheet.payer.to_reimburse)} 보냈어요
                </button>
              </div>
            )}
          </>
        )}
      </BottomSheet>
    </>
  )
}

// ---------- 예산 ----------

function remainingText(c: CategoryUsage): { text: string; color?: string } {
  if (c.budget === null || c.remaining === null) {
    return { text: c.awaiting > 0 ? `예산 없음 · 승인 대기 ${formatWon(c.awaiting)}` : '예산 없음' }
  }
  if (c.state === 'OVER') return { text: `${formatWon(-c.remaining)} 넘었어요`, color: 'var(--danger)' }
  if (c.state === 'AT_RISK') return { text: `대기까지 승인하면 ${formatWon(c.spent + c.awaiting - c.budget)} 넘어요`, color: 'var(--warn)' }
  return { text: `${formatWon(c.remaining)} 남음` }
}

function BudgetView({ orgId, data, isTreasurer }: { orgId: number; data: Settlement; isTreasurer: boolean }) {
  const [editing, setEditing] = useState(false)
  const budgeted = data.categories.filter((c) => c.budget !== null)
  const spentBudgeted = budgeted.reduce((sum, c) => sum + c.spent, 0)
  const awaitingBudgeted = budgeted.reduce((sum, c) => sum + c.awaiting, 0)
  const spent = useCountUp(spentBudgeted)

  return (
    <>
      <section className="card anim-rise" style={stagger(2)} aria-label="예산 합계">
        <div className="card__head" style={{ padding: 0 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-2)', fontSize: 15, fontWeight: 600 }}>
            <Icon name="calendar" size={18} />
            {data.period ? formatPeriod(data.period.start, data.period.end) : '기간 없음 · 처음부터 전부 합산'}
          </span>
          {isTreasurer && (
            <button type="button" className="btn btn--sm btn--secondary" onClick={() => setEditing(true)}>
              {data.period ? '기간 바꾸기' : '기간 정하기'}
            </button>
          )}
        </div>
        {data.budget_total === null ? (
          <p className="caption" style={{ marginTop: 12, lineHeight: 1.6 }}>
            예산을 정한 계정과목이 없어요.{' '}
            {isTreasurer ? (
              <>
                <Link to={`/orgs/${orgId}/settings`} style={{ color: 'var(--primary-text)', fontWeight: 600 }}>
                  설정 → 계정과목
                </Link>
                에서 예산을 넣으면 얼마 남았는지 보여드려요
              </>
            ) : (
              '총무가 설정에서 예산을 넣으면 얼마 남았는지 보여드려요'
            )}
          </p>
        ) : (
          <>
            <p className="big-number" style={{ marginTop: 10, fontSize: 28 }}>
              {formatNumber(spent)}원
              <span style={{ marginLeft: 6, color: 'var(--text-3)', fontSize: 16, fontWeight: 600 }}>
                / {formatWon(data.budget_total)}
              </span>
            </p>
            <div style={{ marginTop: 12 }}>
              <BudgetMeter large label="전체 예산 사용" budget={data.budget_total} spent={spentBudgeted} awaiting={awaitingBudgeted} />
            </div>
            <div className="legend">
              <span>
                <i className="legend__swatch" style={{ background: 'var(--primary)' }} />
                승인됨
              </span>
              {awaitingBudgeted > 0 && (
                <span>
                  <i className="legend__swatch meter__awaiting" />
                  승인 대기 {formatWon(awaitingBudgeted)}
                </span>
              )}
              {spentBudgeted <= data.budget_total ? (
                <span>남은 예산 {formatWon(data.budget_total - spentBudgeted)}</span>
              ) : (
                <span style={{ color: 'var(--danger)', fontWeight: 600 }}>
                  {formatWon(spentBudgeted - data.budget_total)} 넘었어요
                </span>
              )}
            </div>
          </>
        )}
      </section>

      <section className="card card--list anim-rise" style={stagger(3)} aria-label="계정별 예산">
        <div className="card__head">
          <h2 className="card__title">계정별</h2>
          <span className="caption">승인된 지출만 집행액에 들어가요</span>
        </div>
        <div style={{ marginTop: 4 }}>
          {data.categories.map((c) => {
            const remaining = remainingText(c)
            return (
              <div key={c.category_id} className="budget-row">
                <div className="budget-row__head">
                  <CategoryTile category={{ id: c.category_id, name: c.name }} size="md" />
                  <span className="row-item__main">
                    <span className="row-item__title">{c.name}</span>
                    <span className="row-item__sub" style={remaining.color ? { color: remaining.color, fontWeight: 600 } : undefined}>
                      {remaining.text}
                    </span>
                  </span>
                  <span className="row-item__end">
                    <span className="amount">{formatWon(c.spent)}</span>
                    {c.budget !== null && <span className="caption">/ {formatWon(c.budget)}</span>}
                  </span>
                </div>
                {c.budget !== null && (
                  <BudgetMeter label={`${c.name} 예산 사용`} budget={c.budget} spent={c.spent} awaiting={c.awaiting} />
                )}
              </div>
            )
          })}
          {data.categories.length === 0 && <p className="caption" style={{ padding: 8 }}>계정과목이 없어요</p>}
        </div>
      </section>

      {isTreasurer && <PeriodSheet orgId={orgId} open={editing} onClose={() => setEditing(false)} period={data.period} />}
    </>
  )
}

function PeriodSheet({
  orgId,
  open,
  onClose,
  period,
}: {
  orgId: number
  open: boolean
  onClose: () => void
  period: Settlement['period']
}) {
  const update = useUpdateOrg(orgId)
  const { toast } = useFeedback()
  const semester = currentSemester()
  const [start, setStart] = useState(period?.start ?? semester.start)
  const [end, setEnd] = useState(period?.end ?? semester.end)
  const [error, setError] = useState<string | null>(null)
  const year = seoulToday().slice(0, 4)

  function pick(nextStart: string, nextEnd: string) {
    setStart(nextStart)
    setEnd(nextEnd)
  }

  function save(next: { start: string; end: string } | null) {
    setError(null)
    if (next && (!next.start || !next.end)) return setError('시작일과 끝일을 모두 정하세요.')
    if (next && next.start > next.end) return setError('시작일이 끝일보다 늦어요.')
    update.mutate(
      { budget_period_start: next?.start ?? null, budget_period_end: next?.end ?? null },
      {
        onSuccess: () => {
          toast(next ? '예산 기간을 정했어요' : '예산 기간을 없앴어요')
          onClose()
        },
        onError: (e) => setError(errorMessage(e)),
      },
    )
  }

  return (
    <BottomSheet
      open={open}
      onClose={onClose}
      title="예산 기간"
      description="결제일이 이 기간 안인 지출만 예산에서 빠져요. 돌려줄 돈은 기간과 상관없이 전부 보여요"
    >
      <div className="sheet__body">
        <div className="reason-chips">
          <button type="button" className="reason-chip press" onClick={() => pick(semester.start, semester.end)}>
            이번 학기 ({formatPeriod(semester.start, semester.end)})
          </button>
          <button type="button" className="reason-chip press" onClick={() => pick(`${year}-01-01`, `${year}-12-31`)}>
            올해
          </button>
        </div>
        <div className="period-inputs">
          <label className="field">
            <span className="field__label">시작일</span>
            <input className="input" type="date" value={start} onChange={(e) => setStart(e.target.value)} />
          </label>
          <label className="field">
            <span className="field__label">끝일</span>
            <input className="input" type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
          </label>
        </div>
        {error && (
          <p className="message message--error" role="alert" style={{ marginTop: 10 }}>
            <Icon name="alert" size={18} />
            {error}
          </p>
        )}
      </div>
      <div className="sheet__actions">
        {period && (
          <button type="button" className="btn btn--secondary" onClick={() => save(null)} disabled={update.isPending}>
            기간 없애기
          </button>
        )}
        <button type="button" className="btn btn--primary" onClick={() => save({ start, end })} disabled={update.isPending}>
          {update.isPending ? '저장 중…' : '저장'}
        </button>
      </div>
    </BottomSheet>
  )
}
