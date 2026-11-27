import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link, NavLink, useNavigate } from 'react-router'

import { notificationQueries } from '../../api/notifications'
import { PROJECT_CREATOR_LEVELS } from '../../api/organizations'
import { formatDate, PROJECT_STATUS_LABEL } from '../../api/project'
import { useCurrentUser, useLogout, useSelectProject } from '../../hooks/useAuth'
import CreateProjectForm from '../CreateProjectForm'

const WORKSPACE_MENU = [
  { to: '/dashboard', label: '대시보드', icon: 'ri-dashboard-line', end: true },
  { to: '/documents', label: '기준 문서', icon: 'ri-file-shield-2-line' },
  { to: '/notifications', label: '변경 알림', icon: 'ri-notification-3-line' },
  { to: '/submit', label: '변경 제출', icon: 'ri-upload-cloud-2-line' },
  { to: '/assistant', label: 'AI 어시스턴트', icon: 'ri-sparkling-2-line' },
]

const GOVERN_MENU = [
  { label: '기준선', icon: 'ri-anchor-line' },
  { label: '감사 · 추론 로그', icon: 'ri-file-search-line' },
  { label: 'MCP 연동', icon: 'ri-plug-2-line' },
]

interface SidebarProps {
  onNavigate: () => void
}

function Sidebar({ onNavigate }: SidebarProps) {
  const navigate = useNavigate()
  const { user, project, projects, teamName, roleLabel } = useCurrentUser()
  const logout = useLogout()
  const selectProject = useSelectProject()
  const [projectMenuOpen, setProjectMenuOpen] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const canCreateProject = PROJECT_CREATOR_LEVELS.includes(user.user_type)

  const { data: notifications = [] } = useQuery(notificationQueries.received())

  const unreadCount = notifications.filter((n) => n.unread).length

  useEffect(() => {
    if (!createOpen) return
    const closeOnEscape = (e: KeyboardEvent) => e.key === 'Escape' && setCreateOpen(false)
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [createOpen])

  return (
    <div className="flex h-full flex-col">
      <Link to="/" className="flex cursor-pointer items-center gap-2.5 px-5 pb-5 pt-6">
        <span className="flex h-9 w-9 items-center justify-center rounded-md border border-primary-500/30 bg-primary-500/10 font-heading text-[16px] font-semibold text-primary-300 shadow-glow">
          헤
        </span>
        <div className="min-w-0">
          <p className="truncate font-heading text-[16px] font-semibold text-foreground-50">헤디</p>
          <p className="font-label text-[11px] uppercase tracking-[0.18em] text-foreground-500">
            hedy workspace
          </p>
        </div>
      </Link>

      <div className="px-3">
        <button
          type="button"
          onClick={() => setProjectMenuOpen((open) => !open)}
          className="flex w-full cursor-pointer items-center gap-2.5 rounded-md border border-background-600/70 bg-background-800/50 px-3 py-2.5 text-left transition hover:border-background-500 hover:bg-background-700/60"
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-sm bg-secondary-700/70 font-label text-[11px] font-semibold text-secondary-100">
            {project.name.slice(0, 2)}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[14.5px] font-medium text-foreground-100">
              {project.name}
            </span>
            <span className="block truncate text-[12px] text-foreground-500">
              {PROJECT_STATUS_LABEL[project.status]} · {formatDate(project.created_at)} 시작
            </span>
          </span>
          <i
            className={`ri-arrow-down-s-line text-sm text-foreground-500 transition ${projectMenuOpen ? 'rotate-180' : ''}`}
          />
        </button>

        {projectMenuOpen && (
          <div className="mt-1.5 overflow-hidden rounded-md border border-background-600/70 bg-background-900/95 p-1 shadow-panel">
            {projects.map((item) => (
              <button
                key={item.project_id}
                type="button"
                onClick={() => {
                  setProjectMenuOpen(false)
                  selectProject(item.project_id)
                  navigate('/dashboard')
                }}
                className={`flex w-full cursor-pointer items-center justify-between rounded-sm px-2.5 py-2 text-left text-[13px] transition hover:bg-background-700/70 ${item.project_id === project.project_id ? 'text-primary-300' : 'text-foreground-300'}`}
              >
                <span className="truncate">{item.name}</span>
                {item.project_id === project.project_id && (
                  <i className="ri-check-line text-[14.5px]" />
                )}
              </button>
            ))}
            {canCreateProject && (
              <div className="mt-1 border-t border-background-700/80 pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setProjectMenuOpen(false)
                    setCreateOpen(true)
                  }}
                  className="flex w-full cursor-pointer items-center gap-2 rounded-sm px-2.5 py-2 text-[13px] text-foreground-400 transition hover:bg-background-700/70 hover:text-foreground-100"
                >
                  <i className="ri-add-line text-[14.5px]" /> 새 프로젝트
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      <nav className="mt-6 flex-1 overflow-y-auto px-3">
        <p className="px-2 pb-2 font-label text-[11px] uppercase tracking-[0.2em] text-foreground-600">
          Workspace
        </p>
        <ul className="space-y-0.5">
          {WORKSPACE_MENU.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.end}
                onClick={onNavigate}
                className={({ isActive }) =>
                  `group flex cursor-pointer items-center gap-2.5 rounded-md px-2.5 py-2.5 text-[14.5px] transition ${isActive ? 'bg-primary-500/10 text-primary-200' : 'text-foreground-300 hover:bg-background-800/70 hover:text-foreground-100'}`
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      className={`flex h-5 w-5 items-center justify-center rounded-sm ${isActive ? 'text-primary-400' : 'text-foreground-500 group-hover:text-foreground-200'}`}
                    >
                      <i className={`${item.icon} text-[16px]`} />
                    </span>
                    <span className="flex-1 whitespace-nowrap">{item.label}</span>
                    {item.to === '/notifications' && unreadCount > 0 && (
                      <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-primary-500 px-1 font-label text-[11px] font-semibold text-background-950">
                        {unreadCount}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>

        <p className="px-2 pb-2 pt-6 font-label text-[11px] uppercase tracking-[0.2em] text-foreground-600">
          Govern
        </p>
        <ul className="space-y-0.5">
          <li>
            <NavLink
              to="/settings"
              onClick={onNavigate}
              className={({ isActive }) =>
                `flex cursor-pointer items-center gap-2.5 rounded-md px-2.5 py-2.5 text-[14.5px] transition ${isActive ? 'bg-primary-500/10 text-primary-200' : 'text-foreground-300 hover:bg-background-800/70 hover:text-foreground-100'}`
              }
            >
              <span className="flex h-5 w-5 items-center justify-center">
                <i className="ri-team-line text-[16px]" />
              </span>
              <span className="flex-1 whitespace-nowrap">조직 관리</span>
            </NavLink>
          </li>
          {GOVERN_MENU.map((item) => (
            <li key={item.label}>
              <button
                type="button"
                className="flex w-full cursor-pointer items-center gap-2.5 rounded-md px-2.5 py-2.5 text-[14.5px] text-foreground-500 transition hover:bg-background-800/60 hover:text-foreground-200"
              >
                <span className="flex h-5 w-5 items-center justify-center">
                  <i className={`${item.icon} text-[16px]`} />
                </span>
                <span className="flex-1 whitespace-nowrap text-left">{item.label}</span>
                <span className="font-label text-[10px] uppercase tracking-wider text-foreground-600">
                  soon
                </span>
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="border-t border-background-700/70 px-3 py-3">
        <div className="flex items-center gap-2.5 rounded-md px-2 py-1.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-full border border-primary-500/25 bg-primary-500/10 text-[13px] font-medium text-primary-200">
            {user.name.slice(0, 1)}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-[13.5px] text-foreground-100">{user.name}</p>
            <p className="truncate text-[11.5px] text-foreground-500">
              {teamName} · {roleLabel}
            </p>
          </div>
          <button
            type="button"
            onClick={logout}
            aria-label="로그아웃"
            className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-sm text-foreground-500 transition hover:bg-background-700/70 hover:text-foreground-100"
          >
            <i className="ri-logout-box-r-line text-[16px]" />
          </button>
        </div>
      </div>

      {/* 사이드바의 backdrop-blur 가 fixed 기준을 바꾸므로 body 에 띄운다 */}
      {createOpen &&
        createPortal(
          <div className="fixed inset-0 z-[60] flex items-center justify-center px-4">
            <div
              className="absolute inset-0 bg-background-950/75 backdrop-blur-xs"
              onClick={() => setCreateOpen(false)}
            />
            <div className="panel relative w-full max-w-[420px] p-6 shadow-panel">
              <div className="mb-4 flex items-center justify-between">
                <p className="font-heading text-[18px] text-foreground-50">새 프로젝트</p>
                <button
                  type="button"
                  onClick={() => setCreateOpen(false)}
                  aria-label="닫기"
                  className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-sm text-foreground-500 transition hover:bg-background-700/70 hover:text-foreground-100"
                >
                  <i className="ri-close-line text-[16px]" />
                </button>
              </div>
              <CreateProjectForm
                onCreated={() => {
                  setCreateOpen(false)
                  onNavigate()
                }}
              />
            </div>
          </div>,
          document.body,
        )}
    </div>
  )
}

export default Sidebar
