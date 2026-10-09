import type { CSSProperties } from 'react'
import { Link } from 'react-router'
import { useMe } from '../api/auth'
import { useCategories } from '../api/categories'
import { errorMessage } from '../api/client'
import { useExpenses } from '../api/expenses'
import { useMembers, useOrg } from '../api/orgs'
import { useSettlement } from '../api/settlement'
import { ExpenseRow } from '../components/ExpenseRow'
import { Icon, type IconName } from '../components/Icon'
import { RoleBadge } from '../components/RoleBadge'
import { SkeletonRows } from '../components/SkeletonRows'
import { useCountUp } from '../hooks/useCountUp'
import { useOrgId } from '../hooks/useOrgId'
import { formatNumber, formatWon } from '../lib/format'
import { stagger } from '../lib/motion'


type Task = { key: string; to: string; icon: IconName; tone: CSSProperties; title: string; sub: string }

/**
 * 조직 홈: 내가 돌려받을 돈 · 바로가기 · 할 일 · 최근 지출.
 * 돌려받을 돈·승인 대기·보낼 돈은 서버 정산 엔진 값 (GET /settlement), 작성 중·반려는 지출 목록에서.
 */
export function HomePage() {
  const orgId = useOrgId()
  const org = useOrg(orgId)
  const me = useMe()
  const members = useMembers(orgId)
  const expenses = useExpenses(orgId)
  const categories = useCategories(orgId)
  const settlement = useSettlement(orgId)

  const myMembershipId = members.data?.find((m) => m.user_id === me.data?.id)?.membership_id
  const list = expenses.data ?? []
  const mine = myMembershipId === undefined ? [] : list.filter((e) => e.payer.membership_id === myMembershipId)
  const drafts = mine.filter((e) => e.status === 'DRAFT')
  const rejected = mine.filter((e) => e.status === 'REJECTED')
  const role = org.data?.my_role
  const isManager = role === 'TREASURER' || role === 'APPROVER'
  const summary = settlement.data
  const myShare = summary?.me
  const toSend = summary?.scope === 'org' ? summary.payers.filter((p) => p.to_reimburse > 0) : []

  // 돌려받을 돈 = 승인됐고 아직 못 받은 돈 + 승인 대기 (대기는 따로 표시)
  const owed = useCountUp((myShare?.to_reimburse ?? 0) + (myShare?.awaiting_approval ?? 0))
  const loading = expenses.isPending || members.isPending || me.isPending || settlement.isPending

  const tasks: Task[] = [
    drafts.length > 0 && {
      key: 'drafts',
      to: drafts.length === 1 ? `/orgs/${orgId}/expenses/${drafts[0].id}` : `/orgs/${orgId}/expenses?filter=DRAFT`,
      icon: 'receipt',
      tone: { '--tile-bg': 'var(--neutral-weak)', '--tile-fg': 'var(--text-2)' } as CSSProperties,
      title: `작성 중인 지출 ${drafts.length}건`,
      sub: '확인하고 제출하면 승인 요청이 가요',
    },
    rejected.length > 0 && {
      key: 'rejected',
      to: `/orgs/${orgId}/expenses/${rejected[0].id}`,
      icon: 'alert',
      tone: { '--tile-bg': 'var(--danger-weak)', '--tile-fg': 'var(--danger)' } as CSSProperties,
      title: `반려된 내 지출 ${rejected.length}건`,
      sub: `${rejected[0].store_name ?? '가게 이름 없음'} · ${formatWon(rejected[0].amount)}`,
    },
    isManager &&
      summary &&
      summary.awaiting_count > 0 && {
        key: 'org-waiting',
        to: `/orgs/${orgId}/expenses?filter=SUBMITTED`,
        icon: 'checkCircle',
        tone: { '--tile-bg': 'var(--warn-weak)', '--tile-fg': 'var(--warn)' } as CSSProperties,
        title: `승인 기다리는 지출 ${summary.awaiting_count}건`,
        sub: `모두 ${formatWon(summary.awaiting_approval)}`,
      },
    role === 'TREASURER' &&
      toSend.length > 0 && {
        key: 'to-send',
        to: `/orgs/${orgId}/settlement`,
        icon: 'send',
        tone: { '--tile-bg': 'var(--primary-weak)', '--tile-fg': 'var(--primary)' } as CSSProperties,
        title: `${toSend.length}명에게 돌려줄 돈`,
        sub: `모두 ${formatWon(toSend.reduce((total, p) => total + p.to_reimburse, 0))} · 보내고 '보냈어요'로 표시`,
      },
  ].filter((task): task is Task => task !== false && task !== undefined)

  return (
    <>
      <header className="topbar topbar--start">
        <Link to="/orgs" className="org-switch press" aria-label="다른 조직 고르기">
          <span>{org.data?.name ?? ' '}</span>
          <Icon name="chevronDown" size={20} style={{ color: 'var(--text-3)' }} />
        </Link>
      </header>

      <div className="screen screen--with-tabbar">
        <section className="card anim-rise" aria-label="돌려받을 돈" style={stagger(0)}>
          <p style={{ color: 'var(--text-2)', fontSize: 15, fontWeight: 600 }}>돌려받을 돈</p>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginTop: 8 }}>
            <p className="big-number">{formatNumber(owed)}원</p>
            <Link className="btn btn--sm btn--secondary" to={`/orgs/${orgId}/expenses`}>
              내역
            </Link>
          </div>
          <div className="pill-row" style={{ marginTop: 14 }}>
            {loading ? (
              <span className="skeleton" style={{ width: 140, height: 28 }} />
            ) : (myShare?.awaiting_count ?? 0) + (myShare?.expenses.length ?? 0) + drafts.length === 0 ? (
              <span className="caption">영수증을 제출하면 여기에 모여요</span>
            ) : (
              <>
                {myShare && myShare.awaiting_count > 0 && (
                  <span className="pill pill--lg pill--warn">승인 대기 {formatWon(myShare.awaiting_approval)}</span>
                )}
                {myShare && myShare.expenses.length > 0 && (
                  <span className="pill pill--lg pill--primary">받을 돈 {formatWon(myShare.to_reimburse)}</span>
                )}
                {drafts.length > 0 && <span className="pill pill--lg">작성 중 {drafts.length}건</span>}
              </>
            )}
          </div>
        </section>

        <div className="quick-actions anim-rise" style={stagger(1)}>
          <Link className="quick-action quick-action--primary press" to={`/orgs/${orgId}/receipts/new`}>
            <Icon name="camera" />
            영수증 찍기
          </Link>
          <Link className="quick-action press" to={`/orgs/${orgId}/expenses`}>
            <Icon name="receipt" style={{ color: 'var(--text-3)' }} />
            지출 목록
          </Link>
        </div>

        <section className="card card--list anim-rise" aria-label="할 일" style={stagger(2)}>
          <div className="card__head">
            <h2 className="card__title">할 일</h2>
            {org.data && <RoleBadge role={org.data.my_role} />}
          </div>
          <div className="rows" style={{ marginTop: 6 }}>
            {loading && <SkeletonRows count={2} />}
            {!loading && tasks.length === 0 && (
              <p className="message message--ok" style={{ padding: '12px 8px 14px' }}>
                <Icon name="checkCircle" size={20} />
                지금 할 일이 없어요
              </p>
            )}
            {tasks.map((task) => (
              <Link key={task.key} to={task.to} className="row-item press">
                <span className="tile" style={task.tone}>
                  <Icon name={task.icon} size={22} />
                </span>
                <span className="row-item__main">
                  <span className="row-item__title">{task.title}</span>
                  <span className="row-item__sub">{task.sub}</span>
                </span>
                <Icon name="chevronRight" size={20} className="row-item__chevron" />
              </Link>
            ))}
          </div>
        </section>

        <section className="card card--list anim-rise" aria-label="최근 지출" style={stagger(3)}>
          <div className="card__head">
            <h2 className="card__title">최근 지출</h2>
            {list.length > 0 && (
              <Link className="card__more" to={`/orgs/${orgId}/expenses`}>
                전체 보기
              </Link>
            )}
          </div>
          <div className="rows" style={{ marginTop: 6 }}>
            {expenses.isPending && <SkeletonRows count={3} />}
            {expenses.isError && (
              <p className="message message--error" style={{ padding: 8 }}>
                {errorMessage(expenses.error)}
              </p>
            )}
            {expenses.data?.length === 0 && (
              <div className="empty">
                <span className="empty__icon">
                  <Icon name="receipt" />
                </span>
                <p className="empty__title">아직 지출이 없어요</p>
                <p className="empty__desc">결제하고 받은 영수증을 찍으면 여기에 쌓여요</p>
              </div>
            )}
            {list.slice(0, 3).map((e) => (
              <ExpenseRow key={e.id} orgId={orgId} expense={e} categories={categories.data} showDay />
            ))}
          </div>
        </section>
      </div>
    </>
  )
}
