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
