import { useState } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router'

import { useLogout, useSession } from '../../hooks/useAuth'
import Header from './Header'
import NoProjectScreen from './NoProjectScreen'
import Sidebar from './Sidebar'

function AppLayout() {
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const session = useSession()
  const logout = useLogout()

  if (session.unauthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  if (session.noProject) {
    return <NoProjectScreen onLogout={logout} />
  }
  if (!session.ready) return null

  const closeMenu = () => setMobileMenuOpen(false)

  return (
    <div className="min-h-screen text-foreground-100">
      <aside className="fixed left-0 top-0 z-30 hidden h-screen w-[252px] border-r border-background-700/70 bg-background-950/80 backdrop-blur-xl lg:block">
        <Sidebar onNavigate={closeMenu} />
      </aside>

      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-background-950/75 backdrop-blur-xs"
            onClick={closeMenu}
          />
          <aside className="absolute left-0 top-0 h-full w-[272px] border-r border-background-700 bg-background-950">
            <Sidebar onNavigate={closeMenu} />
          </aside>
        </div>
      )}

      <div className="lg:pl-[252px]">
        <Header onOpenMenu={() => setMobileMenuOpen(true)} />
        <main className="mx-auto w-full max-w-[1440px] px-4 py-6 md:px-8 md:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default AppLayout
