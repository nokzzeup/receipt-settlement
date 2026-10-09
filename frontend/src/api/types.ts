// 자주 쓰는 API 타입 별칭 (원본: 자동 생성된 schema.d.ts)
import type { components } from './schema'

type S = components['schemas']

export type User = S['UserOut']
export type MembershipRole = S['MembershipRole']
export type OrgSummary = S['OrgSummary']
export type OrgDetail = S['OrgDetail']
export type Member = S['MemberOut']

export type Category = S['CategoryOut']
export type CategoryCreate = S['CategoryCreate']
export type CategoryUpdate = S['CategoryUpdate']

export type ExpenseStatus = S['ExpenseStatus']
export type ExpenseSummary = S['ExpenseSummary']
export type ExpenseDetail = S['ExpenseDetail']
export type ExpenseItem = S['ExpenseItemOut']
export type ExpenseUpdate = S['ExpenseUpdate']
export type ApprovalAction = S['ApprovalAction']
export type HistoryEntry = S['HistoryEntryOut']
export type BudgetWarning = S['BudgetWarningOut']

export type OrgUpdate = S['OrgUpdate']
export type Settlement = S['SettlementOut']
export type PayerBalance = S['PayerBalanceOut']
export type CategoryUsage = S['CategoryUsageOut']
export type BudgetState = S['BudgetState']
export type Duplicate = S['DuplicateOut']
export type DuplicateReason = S['DuplicateReason']
export type Report = S['ReportOut']

export const ROLE_LABELS: Record<MembershipRole, string> = {
  TREASURER: '총무',
  APPROVER: '승인자',
  MEMBER: '구성원',
}

export const STATUS_LABELS: Record<ExpenseStatus, string> = {
  DRAFT: '작성 중',
  SUBMITTED: '승인 대기',
  APPROVED: '승인됨',
  REJECTED: '반려됨',
}

export const ACTION_LABELS: Record<ApprovalAction, string> = {
  SUBMIT: '제출',
  WITHDRAW: '제출 취소',
  APPROVE: '승인',
  UNAPPROVE: '승인 취소',
  REJECT: '반려',
  REIMBURSE: '환급 완료',
  UNREIMBURSE: '환급 완료 취소',
}
