import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'

import { notificationQueries } from '../api/notifications'
import {
  formatDate,
  PROJECT_STATUS_LABEL,
  projectQueries,
  type ProjectMetric,
} from '../api/project'
import { useCurrentUser } from '../hooks/useAuth'

// 대시보드 상단에 노출하는 지표와 클릭 시 이동할 화면
const METRIC_LINKS: Partial<Record<ProjectMetric['key'], string>> = {
  headDocuments: '/documents',
  pendingApprovals: '/documents',
  confirmRate: '/notifications',
}

function DashboardPage() {
  const { project } = useCurrentUser()
  const { data: metrics = [] } = useQuery(projectQueries.metrics(project.project_id))
  const { data: approvals = [] } = useQuery(projectQueries.pendingApprovals(project.project_id))
  const { data: changes = [] } = useQuery(notificationQueries.confirmedChanges())

  const visibleMetrics = metrics.filter((m) => m.key in METRIC_LINKS)
  const unreadCount = changes.filter((c) => c.unread).length

  return (
    <div className="mx-auto w-full max-w-[1120px] space-y-16 pb-16 md:space-y-20">
      <section className="animate-fade-up">
        <p className="overline">
          {project.name} · {PROJECT_STATUS_LABEL[project.status]} · {formatDate(project.created_at)}{' '}
          시작
        </p>
        <div className="mt-6 flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="font-heading text-[34px] font-light leading-[1.1] tracking-[-0.035em] text-foreground-50 md:text-[46px]">
              {project.name}
            </h1>
            <p className="mt-4 max-w-md text-[15.5px] leading-[1.85] text-foreground-400">
              승인된 산출물만 기준(HEAD)이 되고, 확정된 변경은 영향 팀에 세 줄로 전달됩니다.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Link
              to="/documents"
              className="flex h-10 cursor-pointer items-center whitespace-nowrap rounded-[3px] border border-background-600/80 px-4 text-[13.5px] text-foreground-200 transition hover:border-background-500 hover:bg-background-800/60"
            >
              기준 문서
            </Link>
            <Link
              to="/submit"
              className="flex h-10 cursor-pointer items-center whitespace-nowrap rounded-[3px] bg-foreground-50 px-4 text-[13.5px] font-medium text-background-950 transition hover:bg-foreground-100"
            >
              변경 제출
            </Link>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-px overflow-hidden rounded-[3px] border border-background-700/70 bg-background-700/70 sm:grid-cols-3">
        {visibleMetrics.map((metric, i) => (
          <Link
            key={metric.key}
            to={METRIC_LINKS[metric.key]!}
            style={{ animationDelay: `${i * 70}ms` }}
            className="animate-fade-up cursor-pointer bg-background-950/70 px-6 py-8 transition hover:bg-background-900/70 md:px-7 md:py-10"
          >
            <p className="text-[12px] uppercase tracking-[0.18em] text-foreground-500">
              {metric.label}
            </p>
            <p className="mt-5 font-heading text-[46px] font-light leading-none tracking-[-0.05em] text-foreground-50 md:text-[54px]">
              {metric.value}
              <span className="ml-1.5 font-body text-[14px] font-normal tracking-normal text-foreground-500">
                {metric.unit}
              </span>
            </p>
            <p className="mt-4 text-[13.5px] text-foreground-500">{metric.hint}</p>
          </Link>
        ))}
      </section>

      <section>
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-background-700/60 pb-5">
          <div>
            <h2 className="font-heading text-[19px] font-normal tracking-[-0.02em] text-foreground-50">
              확정된 변경
            </h2>
            <p className="mt-2 text-[13.5px] text-foreground-500">
              승인 후 영향 팀에 발송된 알림과 확인 현황입니다.
            </p>
          </div>
          <Link
            to="/notifications"
            className="flex cursor-pointer items-center gap-1 whitespace-nowrap text-[13px] text-foreground-400 transition hover:text-primary-300"
          >
            알림 전체 <i className="ri-arrow-right-line" />
          </Link>
        </div>

        <div>
          {changes.map((change) => {
            const doneCount = change.teams.filter((t) => t.state === 'done').length
            const allDone = doneCount === change.teams.length

            return (
              <article
                key={change.id}
                className="group flex flex-col gap-4 border-b border-background-800/70 py-7 transition last:border-0 md:flex-row md:items-center md:justify-between md:gap-8"
              >
                <div className="min-w-0 md:flex-1">
                  <div className="flex flex-wrap items-center gap-2.5">
                    {change.unread && (
                      <span className="h-1.5 w-1.5 shrink-0 animate-pulse-dot rounded-full bg-red-400" />
                    )}
                    <Link
                      to={`/documents/${change.docId}`}
                      className="cursor-pointer truncate text-[16px] text-foreground-100 transition hover:text-primary-300"
                    >
                      {change.doc}
                    </Link>
                    <span className="font-label text-[12px] text-foreground-500">
                      {change.from} → <span className="text-primary-300">{change.to}</span>
                    </span>
                    <span className="text-[12.5px] text-foreground-600">{change.time}</span>
                  </div>
                  <p className="mt-2.5 line-clamp-1 text-[14.5px] leading-relaxed text-foreground-400">
                    {change.summary[0]}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-6">
                  <div className="flex flex-col items-end gap-1">
                    <span
                      className={`text-[13px] ${allDone ? 'text-accent-400' : 'text-foreground-400'}`}
                    >
                      확인 {doneCount} / {change.teams.length}
                    </span>
                    <span className="text-[12px] text-foreground-600">
                      영향 팀 {change.teams.length}
                    </span>
                  </div>
                  <Link
                    to={`/documents/${change.docId}`}
                    className="flex h-8 cursor-pointer items-center gap-1 whitespace-nowrap rounded-[3px] border border-background-700/80 px-3 text-[12.5px] text-foreground-300 transition group-hover:border-background-500 hover:text-foreground-50"
                  >
                    변경 보기 <i className="ri-arrow-right-s-line text-[14px]" />
                  </Link>
                </div>
              </article>
            )
          })}
        </div>
      </section>

      <section className="max-w-3xl">
        <div className="flex items-baseline justify-between gap-3">
          <h2 className="font-heading text-[17px] font-normal tracking-[-0.02em] text-foreground-50">
            승인 대기
          </h2>
          <span className="text-[12.5px] text-foreground-500">{approvals.length}건</span>
        </div>
        <ul className="mt-3">
          {approvals.map((approval) => (
            <li key={approval.id} className="border-b border-background-800/70 last:border-0">
              <Link
                to={`/documents/${approval.docId}`}
                className="flex cursor-pointer items-center justify-between gap-4 py-4 transition hover:text-primary-200"
              >
                <span className="min-w-0">
                  <span className="block truncate text-[14.5px] text-foreground-200">
                    {approval.doc} <span className="text-foreground-600">{approval.version}</span>
                  </span>
                  <span className="mt-1 block truncate text-[12.5px] text-foreground-600">
                    {approval.submitter} · {approval.team} · {approval.time}
                  </span>
                </span>
                <i className="ri-arrow-right-s-line shrink-0 text-[16px] text-foreground-600" />
              </Link>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-[12.5px] text-foreground-600">
          미확인 알림 {unreadCount}건 · 승인 대기 문서는 승인권자만 처리할 수 있습니다.
        </p>
      </section>
    </div>
  )
}

export default DashboardPage
