import { Link, NavLink, Outlet, useParams } from 'react-router'

const TABS = [
  { to: 'expenses', label: '지출' },
  { to: 'receipts/new', label: '촬영' },
  { to: 'settlement', label: '정산' },
  { to: 'settings', label: '설정' },
] as const

/** 조직 안 화면 공통 틀: 상단 바 + 하단 탭 (조직 ID는 URL로 관리 → 새로고침·링크 공유해도 유지) */
export function OrgLayout() {
  const { orgId } = useParams()

  return (
    <div className="org-layout">
      <header className="topbar">
        <Link to="/orgs" className="topbar__back">
          ← 조직 목록
        </Link>
        {/* 1단계: 조직 이름 조회로 교체 */}
        <span className="topbar__title">조직 #{orgId}</span>
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
