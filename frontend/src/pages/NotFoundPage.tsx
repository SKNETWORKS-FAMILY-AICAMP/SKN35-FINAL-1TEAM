import { Link, useLocation } from 'react-router'

function NotFoundPage() {
  const { pathname } = useLocation()

  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-4 text-center">
      <p className="overline">404</p>
      <h1 className="mt-4 font-heading text-[28px] font-light text-foreground-50">
        페이지를 찾을 수 없습니다
      </h1>
      <p className="mt-2 font-label text-[13px] text-foreground-500">{pathname}</p>
      <Link
        to="/dashboard"
        className="mt-8 flex h-10 items-center rounded-md bg-foreground-50 px-4 text-[13.5px] font-medium text-background-950 transition hover:bg-foreground-100"
      >
        대시보드로 이동
      </Link>
    </div>
  )
}

export default NotFoundPage
