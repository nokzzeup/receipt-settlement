import { createBrowserRouter, Navigate } from 'react-router'
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
 * 화면 경로
 *   /login                                   로그인
 *   /orgs                                    조직 선택 · 생성 · 초대 코드 참여
 *   /orgs/:orgId/expenses                    지출 목록
 *   /orgs/:orgId/receipts/new                영수증 촬영
 *   /orgs/:orgId/receipts/:receiptId/review  인식 결과 확인·수정
 *   /orgs/:orgId/settlement                  정산 현황
 *   /orgs/:orgId/settings                    조직 설정
 */
export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    children: [
      // 1단계: 로그인 상태면 /orgs 로 보내기
      { index: true, element: <Navigate to="/login" replace /> },
      { path: 'login', element: <LoginPage /> },
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
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
