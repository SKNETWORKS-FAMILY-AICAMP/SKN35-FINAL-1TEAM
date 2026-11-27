import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'

import type { TeamResponse } from '../api/documents'
import {
  notificationQueries,
  respondToNotification,
  type ReceivedNotification,
  type SentChange,
} from '../api/notifications'
import Badge from '../components/Badge'
import Toast from '../components/Toast'
import { useCurrentUser } from '../hooks/useAuth'
import { useToast } from '../hooks/useToast'

type Tab = 'received' | 'sent'

interface Stat {
  label: string
  value: number
  tone: string
  hint: string
}

function receivedStats(items: ReceivedNotification[]): Stat[] {
  return [
    {
      label: '미확인',
      value: items.filter((n) => n.unread).length,
      tone: 'text-red-300',
      hint: '빨간 점으로 표시',
    },
    {
      label: '2일 경과',
      value: items.filter((n) => n.overdue).length,
      tone: 'text-amber-300',
      hint: '자동 리마인드 대상',
    },
    {
      label: '확인 완료',
      value: items.filter((n) => !n.unread).length,
      tone: 'text-accent-400',
      hint: '누가 눌렀는지 기록',
    },
  ]
}

function sentStats(items: SentChange[]): Stat[] {
  const teams = items.flatMap((c) => c.targetTeams)
  const done = teams.filter((t) => t.state === 'done').length
  return [
    { label: '확인 완료 팀', value: done, tone: 'text-accent-400', hint: '영향 팀 응답 기준' },
    {
      label: '미확인 팀',
      value: teams.length - done,
      tone: 'text-amber-300',
      hint: '아직 응답 없음',
    },
    {
      label: '확인 완료한 변경',
      value: items.filter((c) => c.targetTeams.every((t) => t.state === 'done')).length,
      tone: 'text-primary-300',
      hint: '모든 팀 확인',
    },
  ]
}

function SummaryLines({ lines }: { lines: string[] }) {
  return (
    <ol className="mt-3 space-y-1.5 border-l border-background-700/80 pl-3.5">
      {lines.map((line) => (
        <li key={line} className="text-[13.5px] leading-relaxed text-foreground-300">
          {line}
        </li>
      ))}
    </ol>
  )
}

function EmptyState({
  icon,
  iconColor,
  message,
}: {
  icon: string
  iconColor: string
  message: string
}) {
  return (
    <div className="panel flex flex-col items-center gap-2 py-16 text-center">
      <span
        className={`flex h-10 w-10 items-center justify-center rounded-full border border-background-600/70 ${iconColor}`}
      >
        <i className={`${icon} text-lg`} />
      </span>
      <p className="text-[14px] text-foreground-200">{message}</p>
    </div>
  )
}

function NotificationsPage() {
  const queryClient = useQueryClient()
  const toast = useToast()
  const { can } = useCurrentUser()
  const [tab, setTab] = useState<Tab>('received')

  const { data: received = [] } = useQuery(notificationQueries.received())
  const { data: sent = [] } = useQuery(notificationQueries.sent())

  const respond = useMutation({
    mutationFn: ({ id, response }: { id: string; response: TeamResponse }) =>
      respondToNotification(id, response),
    onSuccess: (_, { response }) => {
      queryClient.invalidateQueries({ queryKey: notificationQueries.received().queryKey })
      toast.show(`'${response}'로 응답했습니다. 확인 현황에 기록되었습니다.`)
    },
  })

  const unreadCount = received.filter((n) => n.unread).length
  const stats = tab === 'received' ? receivedStats(received) : sentStats(sent)
  const tabs: { key: Tab; label: string }[] = [
    { key: 'received', label: `받은 변경 ${unreadCount}` },
    { key: 'sent', label: `보낸 변경 ${sent.length}` },
  ]

  return (
    <div className="space-y-5 pb-16">
      <section className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="overline">SHOP · 쇼핑몰 구축 · 알림</p>
          <h1 className="mt-3 font-heading text-[28px] leading-tight text-foreground-50 md:text-[34px]">
            <span className="font-semibold">변경</span>{' '}
            <span className="font-light text-foreground-200">알림</span>
          </h1>
          <p className="mt-2 max-w-2xl text-[14px] leading-relaxed text-foreground-400">
            확정된 변경만 발송됩니다. 내가 받은 변경과 내가 보낸 변경의 확인 상태를 탭으로 나눠
            봅니다.
          </p>
        </div>
        <div className="flex h-9 w-fit items-center rounded-md border border-background-600/70 bg-background-900/60 p-1">
          {tabs.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => setTab(item.key)}
              className={`h-7 cursor-pointer whitespace-nowrap rounded-full px-3.5 font-label text-[12.5px] transition ${tab === item.key ? 'bg-foreground-50 text-background-950' : 'text-foreground-400 hover:text-foreground-100'}`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </section>

      <section className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {stats.map((stat) => (
          <div key={stat.label} className="panel-flat px-4 py-3.5">
            <p className="text-[12.5px] text-foreground-400">{stat.label}</p>
            <p className={`stat-value mt-2 text-[24px] leading-none ${stat.tone}`}>{stat.value}</p>
            <p className="mt-1.5 text-[11.5px] text-foreground-600">{stat.hint}</p>
          </div>
        ))}
      </section>

      {tab === 'received' && (
        <section className="space-y-3">
          {received.map((n) => (
            <article
              key={n.id}
              className={`panel p-4 transition md:p-5 ${n.unread ? 'border-background-600/90' : 'opacity-90 hover:opacity-100'}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="flex min-w-0 items-start gap-2.5">
                  <span
                    className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${n.unread ? 'animate-pulse-dot bg-red-400' : 'bg-background-600'}`}
                  />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Link
                        to={`/documents/${n.docId}`}
                        className="cursor-pointer text-[15px] font-medium text-foreground-50 transition hover:text-primary-300"
                      >
                        {n.doc}
                      </Link>
                      <span className="rounded-sm border border-primary-500/30 bg-primary-500/10 px-1.5 py-0.5 font-label text-[11px] text-primary-300">
                        HEAD {n.version}
                      </span>
                      {n.overdue && (
                        <Badge tone="warning" icon="ri-alarm-warning-line">
                          리마인드 발송됨
                        </Badge>
                      )}
                    </div>
                    <p className="mt-1 text-[11.5px] text-foreground-500">
                      {n.from} · {n.time}
                    </p>
                  </div>
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-1.5">
                  {n.targetTeams.map((team) => (
                    <Badge key={team}>{team}</Badge>
                  ))}
                </div>
              </div>

              <SummaryLines lines={n.summary} />

              <div className="mt-3.5 flex flex-wrap items-center gap-2 border-t border-background-700/60 pt-3">
                <Link
                  to={`/documents/${n.docId}`}
                  className="flex cursor-pointer items-center gap-1 whitespace-nowrap rounded-md border border-background-600/80 px-2.5 py-1.5 text-[12px] text-foreground-200 transition hover:border-primary-500/40 hover:text-primary-200"
                >
                  <i className="ri-contrast-drop-2-line text-[14px]" /> 변경 보기
                </Link>
                {/* TODO: 원본 다운로드 API 연결 */}
                <button
                  type="button"
                  className="flex cursor-pointer items-center gap-1 whitespace-nowrap rounded-md border border-background-600/80 px-2.5 py-1.5 text-[12px] text-foreground-300 transition hover:border-background-500 hover:text-foreground-50"
                >
                  <i className="ri-download-2-line text-[14px]" /> 원본
                </button>
                {n.unread && can.respond ? (
                  <div className="ml-auto flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={() => respond.mutate({ id: n.id, response: '확인 완료' })}
                      className="h-7 cursor-pointer whitespace-nowrap rounded-md bg-foreground-50 px-3 font-label text-[12px] font-medium text-background-950 transition hover:bg-foreground-100"
                    >
                      확인 완료
                    </button>
                    <button
                      type="button"
                      onClick={() => respond.mutate({ id: n.id, response: '영향 없음' })}
                      className="h-7 cursor-pointer whitespace-nowrap rounded-md border border-background-600/80 px-3 font-label text-[12px] text-foreground-200 transition hover:border-background-500 hover:text-foreground-50"
                    >
                      영향 없음
                    </button>
                  </div>
                ) : (
                  <p className="ml-auto flex items-center gap-1 text-[11.5px] text-accent-400">
                    <i className="ri-check-double-line" /> 확인 완료
                  </p>
                )}
              </div>
            </article>
          ))}
          {received.length === 0 && (
            <EmptyState
              icon="ri-check-double-line"
              iconColor="text-accent-400"
              message="받은 변경 알림이 없습니다."
            />
          )}
        </section>
      )}

      {tab === 'sent' && (
        <section className="space-y-3">
          {sent.map((change) => {
            const doneCount = change.targetTeams.filter((t) => t.state === 'done').length
            return (
              <article key={change.id} className="panel p-4 md:p-5">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Link
                        to={`/documents/${change.docId}`}
                        className="cursor-pointer text-[15px] font-medium text-foreground-50 transition hover:text-primary-300"
                      >
                        {change.doc}
                      </Link>
                      <span className="rounded-sm border border-primary-500/30 bg-primary-500/10 px-1.5 py-0.5 font-label text-[11px] text-primary-300">
                        검토 {change.version}
                      </span>
                      <Badge tone={change.status === '확인 완료' ? 'accent' : 'warning'}>
                        {change.status}
                      </Badge>
                    </div>
                    <p className="mt-1 flex items-center gap-1.5 text-[11.5px] text-foreground-500">
                      <i className="ri-upload-cloud-2-line text-[12px]" /> 내가 제출 · {change.time}
                    </p>
                  </div>
                  <span className="shrink-0 font-label text-[12px] text-foreground-400">
                    확인 {doneCount} / {change.targetTeams.length}
                  </span>
                </div>

                <SummaryLines lines={change.summary} />

                <div className="mt-3.5 flex flex-wrap items-center gap-1.5 border-t border-background-700/60 pt-3">
                  <span className="mr-1 font-label text-[11px] uppercase tracking-[0.14em] text-foreground-600">
                    영향 팀
                  </span>
                  {change.targetTeams.map((team) => (
                    <span key={team.name} className="inline-flex flex-col gap-0.5">
                      <span
                        className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11.5px] ${team.state === 'done' ? 'border-accent-500/30 bg-accent-500/10 text-accent-300' : 'border-amber-400/30 bg-amber-400/10 text-amber-300'}`}
                      >
                        <i
                          className={`${team.state === 'done' ? 'ri-check-line' : 'ri-time-line'} text-[12px]`}
                        />
                        {team.name} {team.state === 'done' ? '확인완료' : '미확인'}
                      </span>
                      {team.note && (
                        <span className="pl-1 text-[10.5px] leading-tight text-amber-400">
                          {team.note}
                        </span>
                      )}
                    </span>
                  ))}
                  <Link
                    to={`/documents/${change.docId}`}
                    className="ml-auto flex cursor-pointer items-center gap-1 whitespace-nowrap rounded-md border border-background-600/80 px-2.5 py-1.5 text-[12px] text-foreground-200 transition hover:border-primary-500/40 hover:text-primary-200"
                  >
                    변경 보기 <i className="ri-arrow-right-s-line text-[12px]" />
                  </Link>
                </div>
              </article>
            )
          })}
          {sent.length === 0 && (
            <EmptyState
              icon="ri-upload-cloud-2-line"
              iconColor="text-foreground-500"
              message="보낸 변경이 없습니다."
            />
          )}
        </section>
      )}

      <Toast message={toast.message} textSize="text-[12px]" />
    </div>
  )
}

export default NotificationsPage
