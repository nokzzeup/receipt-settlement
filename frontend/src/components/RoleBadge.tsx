import { ROLE_LABELS, type MembershipRole } from '../api/types'

export function RoleBadge({ role }: { role: MembershipRole }) {
  return <span className={`badge badge--${role.toLowerCase()}`}>{ROLE_LABELS[role]}</span>
}
