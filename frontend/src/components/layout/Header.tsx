import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router'

import { documentQueries } from '../../api/documents'
import { notificationQueries } from '../../api/notifications'
import { useCurrentUser } from '../../hooks/useAuth'

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': '대시보드',
  '/documents': '기준 문서',
  '/notifications': '변경 알림',
  '/submit': '변경 제출',
  '/assistant': 'AI 어시스턴트',
}

const SEARCH_LIMIT = 5

interface HeaderProps {
  onOpenMenu: () => void
}

function Header({ onOpenMenu }: HeaderProps) {
  const { pathname } = useLocation()
  const { project } = useCurrentUser()
  const [keyword, setKeyword] = useState('')
  const [alertsOpen, setAlertsOpen] = useState(false)

  const { data: documents = [] } = useQuery(documentQueries.list())
  const { data: notifications = [] } = useQuery(notificationQueries.received())

  const unread = notifications.filter((n) => n.unread)
  const title = pathname.startsWith('/documents/')
    ? '변경사항 비교'
    : (PAGE_TITLES[pathname] ?? '프로젝트')

  const searchResults = useMemo(() => {
    const q = keyword.trim()
    if (!q) return []
    return documents
      .filter((d) => d.name.includes(q) || d.summary.includes(q) || d.team.includes(q))
      .slice(0, SEARCH_LIMIT)
  }, [documents, keyword])

  return (
    <header className="sticky top-0 z-20 border-b border-background-700/60 bg-background-950/85 backdrop-blur-xl">
      <div className="flex h-16 items-center gap-3 px-4 md:px-8">
        <button
          type="button"
          onClick={onOpenMenu}
          aria-label="메뉴 열기"
          className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-md border border-background-600/70 text-foreground-200 lg:hidden"
        >
          <i className="ri-menu-line text-lg" />
        </button>

        <div className="hidden items-center gap-2 md:flex">
          <span className="font-label text-[12px] uppercase tracking-[0.16em] text-foreground-500">
            {project.name}
          </span>
          <i className="ri-arrow-right-s-line text-foreground-600" />
          <span className="text-[14.5px] text-foreground-200">{title}</span>
          <span className="ml-2 inline-flex items-center gap-1.5 rounded-full border border-accent-500/25 bg-accent-500/10 px-2 py-0.5 font-label text-[11px] uppercase tracking-wider text-accent-400">
            <span className="h-1.5 w-1.5 rounded-full bg-accent-400" /> live
          </span>
        </div>

        <div className="relative ml-auto hidden w-[300px] md:block">
          <span className="pointer-events-none absolute left-3 top-1/2 flex h-4 w-4 -translate-y-1/2 items-center justify-center text-foreground-500">
            <i className="ri-search-line text-[16px]" />
          </span>
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="문서·팀 검색"
            className="h-9 w-full rounded-md border border-background-600/70 bg-background-800/60 pl-9 pr-14 text-[13.5px] text-foreground-100 outline-none transition placeholder:text-foreground-600 focus:border-primary-500/60 focus:bg-background-800"
          />
          <span className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 rounded-sm border border-background-500/70 px-1.5 py-0.5 font-label text-[11px] text-foreground-500">
            ⌘K
          </span>
          {keyword.trim() && (
            <div className="absolute left-0 top-11 w-full overflow-hidden rounded-md border border-background-600/70 p-1 shadow-panel backdrop-blur-xl">
              {searchResults.length === 0 ? (
                <p className="px-3 py-3 text-[13px] text-foreground-500">검색 결과가 없습니다.</p>
              ) : (
                searchResults.map((doc) => (
                  <Link
                    key={doc.id}
                    to={`/documents/${doc.id}`}
                    onClick={() => setKeyword('')}
                    className="flex cursor-pointer items-center gap-2 rounded-sm px-2.5 py-2 transition hover:bg-background-700/70"
                  >
                    <i className="ri-file-text-line text-[14px] text-foreground-500" />
                    <span className="min-w-0 flex-1 truncate text-[13.5px] text-foreground-200">
                      {doc.name}
                    </span>
                    <span className="font-label text-[11px] text-foreground-500">
                      v{doc.version}
                    </span>
                  </Link>
                ))
              )}
            </div>
          )}
        </div>

        <div className="relative ml-auto md:ml-0">
          <button
            type="button"
            onClick={() => setAlertsOpen((open) => !open)}
            aria-label="알림"
            className="relative flex h-9 w-9 cursor-pointer items-center justify-center rounded-md border border-background-600/70 text-foreground-300 transition hover:border-background-500 hover:text-foreground-50"
          >
            <i className="ri-notification-3-line text-[16px]" />
            {unread.length > 0 && (
              <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full border border-background-950 bg-red-500 px-1 font-label text-[10px] font-semibold text-white">
                {unread.length}
              </span>
            )}
          </button>

          {alertsOpen && (
            <div className="absolute right-0 top-11 w-[320px] overflow-hidden rounded-md border border-background-600/70 shadow-panel backdrop-blur-xl">
              <div className="flex items-center justify-between border-b border-background-700/80 px-3.5 py-2.5">
                <p className="font-label text-[12px] uppercase tracking-[0.16em] text-foreground-400">
                  미확인 변경
                </p>
                <Link
                  to="/notifications"
                  onClick={() => setAlertsOpen(false)}
                  className="cursor-pointer text-[12px] text-primary-300 hover:text-primary-200"
                >
                  전체 보기
                </Link>
              </div>
              <ul>
                {unread.map((n) => (
                  <li key={n.id}>
                    <Link
                      to={`/documents/${n.docId}`}
                      onClick={() => setAlertsOpen(false)}
                      className="flex cursor-pointer gap-2.5 border-b border-background-800/80 px-3.5 py-3 transition last:border-0 hover:bg-background-800/70"
                    >
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-red-400" />
                      <span className="min-w-0">
                        <span className="block truncate text-[13.5px] text-foreground-100">
                          {n.doc} <span className="text-foreground-500">{n.version}</span>
                        </span>
                        <span className="mt-0.5 block truncate text-[12px] text-foreground-500">
                          {n.from} · {n.time}
                        </span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <Link
          to="/submit"
          className="hidden h-9 cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-md bg-foreground-50 px-3.5 text-[13.5px] font-medium text-background-950 transition hover:bg-foreground-100 sm:flex"
        >
          <i className="ri-upload-cloud-2-line text-[16px]" /> 변경 제출
        </Link>
      </div>
    </header>
  )
}

export default Header
