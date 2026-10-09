import { ROLE_LABELS, type MembershipRole } from '../api/types'

export function RoleBadge({ role }: { role: MembershipRole }) {
  return <span className={`pill pill--${role.toLowerCase()}`}>{ROLE_LABELS[role]}</span>
}
