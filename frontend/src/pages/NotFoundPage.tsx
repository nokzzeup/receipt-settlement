import { Link } from 'react-router'
import { Page } from '../components/Page'

export function NotFoundPage() {
  return (
    <Page title="페이지를 찾을 수 없어요" subtitle="주소가 바뀌었거나 없는 화면이에요">
      <Link className="btn btn--secondary btn--block" to="/">
        처음으로
      </Link>
    </Page>
  )
}
