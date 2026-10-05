import { createBrowserRouter, Navigate } from 'react-router'
import { HomeRedirect, RequireAuth } from './components/RequireAuth'
import { OrgLayout } from './layouts/OrgLayout'
import { RootLayout } from './layouts/RootLayout'
import { ExpenseListPage } from './pages/ExpenseListPage'
import { LoginPage } from './pages/LoginPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { OrgSelectPage } from './pages/OrgSelectPage'
import { OrgSettingsPage } from './pages/OrgSettingsPage'
import { ReceiptCapturePage } from './pages/ReceiptCapturePage'
import { ReceiptReviewPage } from './pages/ReceiptReviewPage'
import { SettlementPage } from './pages/SettlementPage'

/**
 * 화면 경로 (/login 외에는 전부 로그인 필요)
 *   /login                                   로그인 · 회원가입
 *   /orgs                                    조직 선택 · 생성 · 초대 코드 참여
 *   /orgs/:orgId/expenses                    지출 목록
 *   /orgs/:orgId/receipts/new                영수증 촬영
 *   /orgs/:orgId/receipts/:receiptId/review  인식 결과 확인·수정
 *   /orgs/:orgId/settlement                  정산 현황
 *   /orgs/:orgId/settings                    조직 설정 (초대 코드, 구성원 역할)
 */
export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    children: [
      { index: true, element: <HomeRedirect /> },
      { path: 'login', element: <LoginPage /> },
      {
        element: <RequireAuth />,
        children: [
          { path: 'orgs', element: <OrgSelectPage /> },
          {
            path: 'orgs/:orgId',
            element: <OrgLayout />,
            children: [
              { index: true, element: <Navigate to="expenses" replace /> },
              { path: 'expenses', element: <ExpenseListPage /> },
              { path: 'receipts/new', element: <ReceiptCapturePage /> },
              { path: 'receipts/:receiptId/review', element: <ReceiptReviewPage /> },
              { path: 'settlement', element: <SettlementPage /> },
              { path: 'settings', element: <OrgSettingsPage /> },
            ],
          },
        ],
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
