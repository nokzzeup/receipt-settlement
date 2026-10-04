import { Link } from 'react-router'
import { Page } from '../components/Page'

/** 조직 선택 / 새 조직 만들기 / 초대 코드로 참여 */
export function OrgSelectPage() {
  return (
    <Page title="조직 선택" todo="1단계: 내 조직 목록, 조직 생성, 초대 코드 참여 API 연결">
      <section className="card">
        <h2 className="card__title">내 조직</h2>
        <Link to="/orgs/1/expenses">예시 조직 #1 (개발용 링크)</Link>
      </section>

      <section className="card">
        <h2 className="card__title">새 조직 만들기</h2>
        <form className="stack" onSubmit={(e) => e.preventDefault()}>
          <input className="input" placeholder="조직 이름 (예: 컴공 학생회)" />
          <button className="button" type="submit" disabled>
            만들기
          </button>
        </form>
      </section>

      <section className="card">
        <h2 className="card__title">초대 코드로 참여</h2>
        <form className="stack" onSubmit={(e) => e.preventDefault()}>
          <input className="input" placeholder="초대 코드" autoCapitalize="characters" />
          <button className="button" type="submit" disabled>
            참여
          </button>
        </form>
      </section>
    </Page>
  )
}
