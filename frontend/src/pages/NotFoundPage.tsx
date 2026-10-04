import { Link } from 'react-router'
import { Page } from '../components/Page'

export function NotFoundPage() {
  return (
    <Page title="페이지를 찾을 수 없어요">
      <Link to="/">처음으로</Link>
    </Page>
  )
}
