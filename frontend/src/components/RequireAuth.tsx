import { Navigate, Outlet, useLocation } from 'react-router'
import { getToken } from '../auth/token'

/** 로그인해야 들어갈 수 있는 화면들의 바깥 틀. 토큰이 없으면 로그인 화면으로 (끝나면 원래 화면으로 돌아옴) */
export function RequireAuth() {
  const location = useLocation()
  if (!getToken()) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}

/** 첫 화면: 로그인 상태면 조직 목록, 아니면 로그인 */
export function HomeRedirect() {
  return <Navigate to={getToken() ? '/orgs' : '/login'} replace />
}
