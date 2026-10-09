import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { logout, useMe } from '../api/auth'
import { errorMessage } from '../api/client'
import { useMembers, useOrg, useRegenerateInviteCode, useUpdateRole } from '../api/orgs'
import { ROLE_LABELS, type MembershipRole } from '../api/types'
import { CategorySettings } from '../components/CategorySettings'
import { Icon } from '../components/Icon'
import { LargeTitle } from '../components/Page'
import { RoleBadge } from '../components/RoleBadge'
import { SkeletonRows } from '../components/SkeletonRows'
import { useFeedback } from '../feedback/context'
import { useOrgId } from '../hooks/useOrgId'
import { stagger } from '../lib/motion'

const ROLES: MembershipRole[] = ['TREASURER', 'APPROVER', 'MEMBER']

/** ABCD2345 → ABCD-2345 (읽기 쉽게. 참여할 때 하이픈은 있어도 없어도 됨) */
const formatCode = (code: string) => `${code.slice(0, 4)}-${code.slice(4)}`

/** 이름 첫 글자 (구성원 동그라미) */
const initialOf = (name: string) => name.trim().slice(0, 1) || '?'

export function OrgSettingsPage() {
  const orgId = useOrgId()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast, confirm } = useFeedback()
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
      toast('초대 코드를 복사했어요')
      setTimeout(() => setCopied(false), 1800)
    } catch {
      // 복사가 막힌 환경(http로 폰 접속 등) → 화면의 코드를 직접 보고 전달
      toast('복사가 막혀 있어요. 화면의 코드를 직접 알려주세요')
    }
  }

  async function handleRegenerate() {
    const ok = await confirm({
      title: '초대 코드를 새로 만들까요?',
      message: '지금 코드는 바로 못 쓰게 돼요. 이미 들어온 구성원은 그대로예요.',
      confirmLabel: '새로 만들기',
    })
    if (ok) regenerate.mutate(undefined, { onSuccess: () => toast('새 초대 코드를 만들었어요') })
  }

  async function handleLogout() {
    const ok = await confirm({ title: '로그아웃할까요?', confirmLabel: '로그아웃' })
    if (!ok) return
    logout(queryClient)
    navigate('/login', { replace: true })
  }

  return (
    <>
      <div className="topbar-spacer" aria-hidden="true" />
      <div className="screen screen--with-tabbar">
        <LargeTitle title="설정" />

        <section className="card anim-rise" style={stagger(1)} aria-label="조직">
          <p style={{ fontSize: 19, fontWeight: 700, letterSpacing: '-0.02em' }}>{org.data?.name ?? ' '}</p>
          <p className="caption" style={{ marginTop: 4, fontSize: 14 }}>
            {members.data ? `구성원 ${members.data.length}명` : ' '}
            {org.data && ` · 내 역할 ${ROLE_LABELS[org.data.my_role]}`}
          </p>
          <div className="invite-box">
            <p className="field__label">초대 코드</p>
            {isTreasurer && inviteCode ? (
              <>
                <p key={inviteCode} className="invite-code anim-pop">
                  {formatCode(inviteCode)}
                </p>
                <p className="caption" style={{ marginTop: 4 }}>
                  이 코드를 알려주면 '구성원'으로 들어올 수 있어요
                </p>
                <div className="btn-row" style={{ marginTop: 14 }}>
                  <button type="button" className="btn btn--md btn--weak" onClick={copyCode}>
                    <Icon key={String(copied)} name={copied ? 'check' : 'copy'} size={18} className={copied ? 'anim-pop' : undefined} />
                    {copied ? '복사했어요' : '복사'}
                  </button>
                  <button type="button" className="btn btn--md btn--secondary" onClick={handleRegenerate} disabled={regenerate.isPending}>
                    새로 만들기
                  </button>
                </div>
                {regenerate.isError && <p className="message message--error">{errorMessage(regenerate.error)}</p>}
              </>
            ) : (
              <p className="caption" style={{ marginTop: 4 }}>
                초대 코드는 총무만 볼 수 있어요
              </p>
            )}
          </div>
        </section>

        <div className="anim-rise" style={stagger(2)}>
          <CategorySettings orgId={orgId} canManage={isTreasurer} />
        </div>

        <section className="card card--list anim-rise" style={stagger(3)} aria-label="구성원">
          <div className="card__head">
            <h2 className="card__title">구성원 {members.data ? `${members.data.length}명` : ''}</h2>
          </div>
          {members.isPending && <SkeletonRows count={3} />}
          {members.isError && <p className="message message--error">{errorMessage(members.error)}</p>}
          <div className="rows" style={{ marginTop: 6 }}>
            {members.data?.map((m) => (
              <div key={m.membership_id} className="row-item" style={{ minHeight: 60 }}>
                <span className="tile tile--md tile--round" style={{ fontSize: 15 }}>
                  {initialOf(m.name)}
                </span>
                <span className="row-item__main">
                  <span className="row-item__title">
                    {m.name}
                    {m.user_id === me.data?.id && <span style={{ color: 'var(--text-3)', fontWeight: 500 }}> (나)</span>}
                  </span>
                  <span className="row-item__sub">{m.email}</span>
                </span>
                {isTreasurer ? (
                  <select
                    className="select"
                    aria-label={`${m.name} 역할`}
                    value={m.role}
                    disabled={updateRole.isPending}
                    onChange={(e) =>
                      updateRole.mutate(
                        { membershipId: m.membership_id, role: e.target.value as MembershipRole },
                        { onSuccess: () => toast(`${m.name}님 역할을 바꿨어요`) },
                      )
                    }
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
              </div>
            ))}
          </div>
          {updateRole.isError && (
            <p className="message message--error" style={{ padding: '0 8px 8px' }}>
              {errorMessage(updateRole.error)}
            </p>
          )}
          <p className="caption" style={{ padding: '6px 8px 12px', lineHeight: 1.6 }}>
            총무: 초대 코드·역할·계정과목 관리 · 승인자: 지출 승인/반려 · 구성원: 영수증 등록
          </p>
        </section>

        <section className="card anim-rise" style={{ ...stagger(4), padding: '6px 12px' }} aria-label="계정">
          <Link to="/orgs" className="row-item press" style={{ minHeight: 52 }}>
            <Icon name="swap" size={22} style={{ color: 'var(--text-3)' }} />
            <span className="row-item__main">
              <span className="row-item__title">다른 조직으로</span>
            </span>
            <Icon name="chevronRight" size={20} className="row-item__chevron" />
          </Link>
          <button type="button" className="row-item press" style={{ minHeight: 52, color: 'var(--danger)' }} onClick={handleLogout}>
            <Icon name="logout" size={22} />
            <span className="row-item__main">
              <span className="row-item__title">
                로그아웃{me.data && <span style={{ color: 'var(--text-3)', fontWeight: 500 }}> · {me.data.email}</span>}
              </span>
            </span>
          </button>
        </section>
      </div>
    </>
  )
}
