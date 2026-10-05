import { Link, NavLink, Outlet } from 'react-router'
import { errorMessage } from '../api/client'
import { useOrg } from '../api/orgs'
import { Page } from '../components/Page'
import { RoleBadge } from '../components/RoleBadge'
import { useOrgId } from '../hooks/useOrgId'

const TABS = [
  { to: 'expenses', label: '지출' },
  { to: 'receipts/new', label: '촬영' },
  { to: 'settlement', label: '정산' },
  { to: 'settings', label: '설정' },
] as const

/** 조직 안 화면 공통 틀: 상단 바 + 하단 탭 (조직 ID는 URL로 관리 → 새로고침·링크 공유해도 유지) */
export function OrgLayout() {
  const orgId = useOrgId()
  const org = useOrg(orgId)

  if (org.isError || Number.isNaN(orgId)) {
    return (
      <Page title="조직을 열 수 없어요">
        <p className="muted">{Number.isNaN(orgId) ? '주소가 올바르지 않습니다.' : errorMessage(org.error)}</p>
        <Link to="/orgs">← 조직 목록으로</Link>
      </Page>
    )
  }

  return (
    <div className="org-layout">
      <header className="topbar">
        <Link to="/orgs" className="topbar__back">
          ← 조직 목록
        </Link>
        <span className="topbar__title">
          {org.data ? (
            <>
              {org.data.name} <RoleBadge role={org.data.my_role} />
            </>
          ) : (
            '…'
          )}
        </span>
      </header>

      <main className="org-layout__content">
        <Outlet />
      </main>

      <nav className="tabbar" aria-label="조직 메뉴">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) => (isActive ? 'tabbar__item tabbar__item--active' : 'tabbar__item')}
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
