import { Outlet } from 'react-router'
import { ApiStatus } from '../components/ApiStatus'
import { FeedbackProvider } from '../feedback/FeedbackProvider'

export function RootLayout() {
  return (
    <FeedbackProvider>
      <div className="app">
        {import.meta.env.DEV && <ApiStatus />}
        <Outlet />
      </div>
    </FeedbackProvider>
  )
}
