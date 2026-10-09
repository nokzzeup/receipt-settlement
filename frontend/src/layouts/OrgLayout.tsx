import { Link, NavLink, Outlet, useLocation, useMatch } from 'react-router'
import { errorMessage } from '../api/client'
import { useOrg } from '../api/orgs'
import { Icon, type IconName } from '../components/Icon'
import { Page } from '../components/Page'
import { useOrgId } from '../hooks/useOrgId'

type Tab = { to: string; label: string; icon: IconName; end?: boolean }

const LEFT_TABS: Tab[] = [
  { to: '', label: '홈', icon: 'home', end: true },
  { to: 'expenses', label: '지출', icon: 'receipt' },
]
const RIGHT_TABS: Tab[] = [
  { to: 'settlement', label: '정산', icon: 'wallet' },
  { to: 'settings', label: '설정', icon: 'sliders' },
]

/**
 * 조직 안 화면 공통 틀: 아래 탭(홈·지출·찍기·정산·설정) + 화면 바뀔 때 살짝 떠오르는 움직임.
 * 조직 ID는 URL로 관리 → 새로고침·링크 공유해도 유지. 영수증 찍기·지출 상세는 할 일에 집중하게 탭을 숨긴다.
 */
export function OrgLayout() {
  const orgId = useOrgId()
  const org = useOrg(orgId)
  const location = useLocation()
  const onCapture = useMatch('/orgs/:orgId/receipts/new')
  const onDetail = useMatch('/orgs/:orgId/expenses/:expenseId')
  const showTabbar = !onCapture && !onDetail

  if (org.isError || Number.isNaN(orgId)) {
    return (
      <Page title="조직을 열 수 없어요" subtitle={Number.isNaN(orgId) ? '주소가 올바르지 않아요.' : errorMessage(org.error)}>
        <Link className="btn btn--secondary btn--block" to="/orgs">
          조직 목록으로
        </Link>
      </Page>
    )
  }

  const base = `/orgs/${orgId}`
  const tab = (t: Tab) => (
    <NavLink key={t.label} to={t.to ? `${base}/${t.to}` : base} end={t.end} className="tabbar__item press">
      <Icon name={t.icon} />
      {t.label}
    </NavLink>
  )

  return (
    <>
      {/* 주소가 바뀔 때마다 새로 그려서 등장 움직임을 다시 */}
      <div key={location.pathname} className="route-enter">
        <Outlet />
      </div>

      {showTabbar && (
        <nav className="tabbar" aria-label="조직 메뉴">
          {LEFT_TABS.map(tab)}
          <NavLink to={`${base}/receipts/new`} className="tabbar__item tabbar__capture" aria-label="영수증 찍기">
            <span className="tabbar__capture-button">
              <Icon name="camera" size={26} />
            </span>
            <span aria-hidden="true">찍기</span>
          </NavLink>
          {RIGHT_TABS.map(tab)}
        </nav>
      )}
    </>
  )
}
