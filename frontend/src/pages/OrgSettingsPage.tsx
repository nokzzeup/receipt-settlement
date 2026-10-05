import { useState } from 'react'
import { useMe } from '../api/auth'
import { errorMessage } from '../api/client'
import { useMembers, useOrg, useRegenerateInviteCode, useUpdateRole } from '../api/orgs'
import { ROLE_LABELS, type MembershipRole } from '../api/types'
import { CategorySettings } from '../components/CategorySettings'
import { Page } from '../components/Page'
import { RoleBadge } from '../components/RoleBadge'
import { useOrgId } from '../hooks/useOrgId'

const ROLES: MembershipRole[] = ['TREASURER', 'APPROVER', 'MEMBER']

/** ABCD2345 → ABCD-2345 (읽기 쉽게. 참여할 때 하이픈은 있어도 없어도 됨) */
const formatCode = (code: string) => `${code.slice(0, 4)}-${code.slice(4)}`

export function OrgSettingsPage() {
  const orgId = useOrgId()
  const org = useOrg(orgId)
  const members = useMembers(orgId)
  const me = useMe()
  const regenerate = useRegenerateInviteCode(orgId)
  const updateRole = useUpdateRole(orgId)
  const [copied, setCopied] = useState(false)

  const isTreasurer = org.data?.my_role === 'TREASURER'
  const inviteCode = org.data?.invite_code

  async function copyCode() {
    if (!inviteCode) return
    try {
      await navigator.clipboard.writeText(formatCode(inviteCode))
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // 복사가 막힌 환경(http 폰 접속 등) → 코드를 직접 보고 전달
    }
  }

  function handleRegenerate() {
    if (window.confirm('초대 코드를 새로 만들까요? 지금 코드는 바로 못 쓰게 됩니다.')) regenerate.mutate()
  }

  return (
    <Page title="조직 설정">
      <section className="card">
        <h2 className="card__title">초대 코드</h2>
        {isTreasurer && inviteCode ? (
          <div className="stack">
            <p className="invite-code">{formatCode(inviteCode)}</p>
            <p className="muted">구성원에게 이 코드를 알려주세요. 참여하면 '구성원' 역할로 들어옵니다.</p>
            <div className="row">
              <button type="button" className="button" onClick={copyCode}>
                {copied ? '복사됨!' : '복사'}
              </button>
              <button type="button" className="button button--ghost" onClick={handleRegenerate} disabled={regenerate.isPending}>
                재발급
              </button>
            </div>
            {regenerate.isError && <p className="error">{errorMessage(regenerate.error)}</p>}
          </div>
        ) : (
          <p className="muted">초대 코드는 총무만 볼 수 있어요.</p>
        )}
      </section>

      <section className="card">
        <h2 className="card__title">구성원 {members.data ? `${members.data.length}명` : ''}</h2>
        {members.isPending && <p className="muted">불러오는 중…</p>}
        {members.isError && <p className="error">{errorMessage(members.error)}</p>}
        {members.data && (
          <ul className="list">
            {members.data.map((m) => (
              <li key={m.membership_id} className="list__item">
                <span className="list__main">
                  <span>
                    {m.name}
                    {m.user_id === me.data?.id && <span className="muted"> (나)</span>}
                  </span>
                  <span className="list__sub">{m.email}</span>
                </span>
                {isTreasurer ? (
                  <select
                    className="select"
                    aria-label={`${m.name} 역할`}
                    value={m.role}
                    disabled={updateRole.isPending}
                    onChange={(e) => updateRole.mutate({ membershipId: m.membership_id, role: e.target.value as MembershipRole })}
                  >
                    {ROLES.map((role) => (
                      <option key={role} value={role}>
                        {ROLE_LABELS[role]}
                      </option>
                    ))}
                  </select>
                ) : (
                  <RoleBadge role={m.role} />
                )}
              </li>
            ))}
          </ul>
        )}
        {updateRole.isError && <p className="error">{errorMessage(updateRole.error)}</p>}
        <p className="muted">총무: 초대 코드·역할·계정과목 관리 · 승인자: 지출 승인/반려 · 구성원: 영수증 등록</p>
      </section>

      <CategorySettings orgId={orgId} canManage={isTreasurer} />
    </Page>
  )
}
