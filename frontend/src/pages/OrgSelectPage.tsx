import { useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router'
import { logout, useMe } from '../api/auth'
import { errorMessage } from '../api/client'
import { useCreateOrg, useJoinOrg, useMyOrgs } from '../api/orgs'
import { Page } from '../components/Page'
import { RoleBadge } from '../components/RoleBadge'

/** 조직 선택 / 새 조직 만들기 / 초대 코드로 참여 */
export function OrgSelectPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
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
    joinOrg.mutate(code, { onSuccess: (org) => navigate(`/orgs/${org.id}/expenses`) })
  }

  function handleLogout() {
    logout(queryClient)
    navigate('/login', { replace: true })
  }

  return (
    <Page title="조직 선택">
      <div className="row row--between">
        <span className="muted">{me.data ? `${me.data.name} (${me.data.email})` : ' '}</span>
        <button type="button" className="link-button" onClick={handleLogout}>
          로그아웃
        </button>
      </div>

      <section className="card">
        <h2 className="card__title">내 조직</h2>
        {orgs.isPending && <p className="muted">불러오는 중…</p>}
        {orgs.isError && <p className="error">{errorMessage(orgs.error)}</p>}
        {orgs.data?.length === 0 && <p className="muted">아직 참여한 조직이 없어요. 새로 만들거나 초대 코드로 참여하세요.</p>}
        {orgs.data && orgs.data.length > 0 && (
          <ul className="list">
            {orgs.data.map((org) => (
              <li key={org.id}>
                <Link className="list__item list__link" to={`/orgs/${org.id}/expenses`}>
                  <span className="list__main">{org.name}</span>
                  <span className="row">
                    <span className="muted">{org.member_count}명</span>
                    <RoleBadge role={org.my_role} />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h2 className="card__title">새 조직 만들기</h2>
        <form className="stack" onSubmit={handleCreate}>
          <input
            className="input"
            placeholder="조직 이름 (예: 컴공 학생회)"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            maxLength={100}
            required
          />
          {createOrg.isError && <p className="error">{errorMessage(createOrg.error)}</p>}
          <button className="button" type="submit" disabled={createOrg.isPending || !newName.trim()}>
            만들기 (내가 총무가 됨)
          </button>
        </form>
      </section>

      <section className="card">
        <h2 className="card__title">초대 코드로 참여</h2>
        <form className="stack" onSubmit={handleJoin}>
          <input
            className="input input--code"
            placeholder="초대 코드 8자리"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            autoCapitalize="characters"
            autoComplete="off"
            required
          />
          {joinOrg.isError && <p className="error">{errorMessage(joinOrg.error)}</p>}
          <button className="button" type="submit" disabled={joinOrg.isPending || !code.trim()}>
            참여
          </button>
        </form>
      </section>
    </Page>
  )
}
