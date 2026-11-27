import { useState } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router'

import { useLogout, useSession } from '../../hooks/useAuth'
import Header from './Header'
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
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 px-4 text-center">
        <p className="overline">no project</p>
        <h1 className="font-heading text-[24px] font-light text-foreground-50">
          참여 중인 프로젝트가 없습니다
        </h1>
        <p className="text-[13.5px] text-foreground-500">
          프로젝트 오너에게 멤버 추가를 요청해 주세요.
        </p>
        <button
          type="button"
          onClick={logout}
          className="mt-4 h-9 cursor-pointer rounded-md border border-background-600/80 px-4 text-[13px] text-foreground-200 transition hover:bg-background-800/60"
        >
          로그아웃
        </button>
      </div>
    )
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
