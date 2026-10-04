import { Outlet } from 'react-router'
import { ApiStatus } from '../components/ApiStatus'

export function RootLayout() {
  return (
    <div className="app">
      {import.meta.env.DEV && <ApiStatus />}
      <Outlet />
    </div>
  )
}
