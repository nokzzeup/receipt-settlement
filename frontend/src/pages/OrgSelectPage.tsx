import { useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { logout, useMe } from '../api/auth'
import { errorMessage } from '../api/client'
import { useCreateOrg, useJoinOrg, useMyOrgs } from '../api/orgs'
import { Icon } from '../components/Icon'
import { LargeTitle } from '../components/Page'
import { RoleBadge } from '../components/RoleBadge'
import { SkeletonRows } from '../components/SkeletonRows'
import { useFeedback } from '../feedback/context'
import { stagger } from '../lib/motion'

/** 조직 선택 / 새 조직 만들기 / 초대 코드로 참여 */
export function OrgSelectPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { confirm } = useFeedback()
  const me = useMe()
  const orgs = useMyOrgs()
  const createOrg = useCreateOrg()
  const joinOrg = useJoinOrg()
  const [newName, setNewName] = useState('')
  const [code, setCode] = useState('')

  function handleCreate(e: FormEvent) {
    e.preventDefault()
    // 만들고 나면 초대 코드를 바로 공유할 수 있게 설정 화면으로
    createOrg.mutate(newName, { onSuccess: (org) => navigate(`/orgs/${org.id}/settings`) })
  }

  function handleJoin(e: FormEvent) {
    e.preventDefault()
    joinOrg.mutate(code, { onSuccess: (org) => navigate(`/orgs/${org.id}`) })
  }

  async function handleLogout() {
    if (!(await confirm({ title: '로그아웃할까요?', confirmLabel: '로그아웃' }))) return
    logout(queryClient)
    navigate('/login', { replace: true })
  }

  return (
    <>
      <header className="topbar topbar--start">
        <span className="caption" style={{ paddingLeft: 6 }}>
          {me.data ? `${me.data.name} · ${me.data.email}` : ' '}
        </span>
        <button type="button" className="btn btn--sm btn--text" onClick={handleLogout}>
          로그아웃
        </button>
      </header>

      <div className="screen">
        <LargeTitle title="어느 조직으로 갈까요?" subtitle="학생회·동아리·팀마다 지출을 따로 관리해요" />

        <section className="card card--list anim-rise" style={stagger(1)} aria-label="내 조직">
          <div className="card__head">
            <h2 className="card__title">내 조직</h2>
          </div>
          {orgs.isPending && <SkeletonRows count={2} />}
          {orgs.isError && <p className="message message--error">{errorMessage(orgs.error)}</p>}
          {orgs.data?.length === 0 && (
            <p className="caption" style={{ padding: '12px 8px' }}>
              아직 참여한 조직이 없어요. 새로 만들거나 초대 코드로 참여하세요
            </p>
          )}
          <ul className="rows" style={{ marginTop: 6 }}>
            {orgs.data?.map((org) => (
              <li key={org.id}>
                <Link className="row-item press" to={`/orgs/${org.id}`}>
                  <span className="tile" style={{ background: 'var(--primary-weak)', color: 'var(--primary-text)' }}>
                    {org.name.trim().slice(0, 1)}
                  </span>
                  <span className="row-item__main">
                    <span className="row-item__title">{org.name}</span>
                    <span className="row-item__sub">구성원 {org.member_count}명</span>
                  </span>
                  <RoleBadge role={org.my_role} />
                  <Icon name="chevronRight" size={20} className="row-item__chevron" />
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section className="card anim-rise" style={stagger(2)} aria-label="새 조직 만들기">
          <h2 className="card__title">새 조직 만들기</h2>
          <p className="caption" style={{ marginTop: 4 }}>
            만든 사람이 총무가 되고, 초대 코드로 구성원을 불러요
          </p>
          <form className="form-stack" style={{ marginTop: 14 }} onSubmit={handleCreate}>
            <input
              className="input"
              placeholder="조직 이름 (예: 컴공 학생회)"
              aria-label="조직 이름"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              maxLength={100}
              required
            />
            {createOrg.isError && <p className="message message--error">{errorMessage(createOrg.error)}</p>}
            <button className="btn btn--primary btn--block" type="submit" disabled={createOrg.isPending || !newName.trim()}>
              만들기
            </button>
          </form>
        </section>

        <section className="card anim-rise" style={stagger(3)} aria-label="초대 코드로 참여">
          <h2 className="card__title">초대 코드로 참여</h2>
          <p className="caption" style={{ marginTop: 4 }}>
            총무에게 받은 8자리 코드를 넣어주세요
          </p>
          <form className="form-stack" style={{ marginTop: 14 }} onSubmit={handleJoin}>
            <input
              className="input input--code"
              placeholder="초대 코드 8자리"
              aria-label="초대 코드"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              autoCapitalize="characters"
              autoComplete="off"
              required
            />
            {joinOrg.isError && <p className="message message--error">{errorMessage(joinOrg.error)}</p>}
            <button className="btn btn--secondary btn--block" type="submit" disabled={joinOrg.isPending || !code.trim()}>
              참여
            </button>
          </form>
        </section>
      </div>
    </>
  )
}
