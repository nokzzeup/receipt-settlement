// 자주 쓰는 API 타입 별칭 (원본: 자동 생성된 schema.d.ts)
import type { components } from './schema'

type S = components['schemas']

export type User = S['UserOut']
export type MembershipRole = S['MembershipRole']
export type OrgSummary = S['OrgSummary']
export type OrgDetail = S['OrgDetail']
export type Member = S['MemberOut']

export const ROLE_LABELS: Record<MembershipRole, string> = {
  TREASURER: '총무',
  APPROVER: '승인자',
  MEMBER: '구성원',
}
