import { queryOptions } from '@tanstack/react-query'

import { request } from './client'
import type { TeamResponse } from './documents'

export interface TeamCheck {
  name: string
  state: 'pending' | 'done'
  by: string
  note?: string
}

export interface ConfirmedChange {
  id: string
  docId: string
  doc: string
  from: string
  to: string
  time: string
  unread: boolean
  summary: string[]
  teams: TeamCheck[]
}

export interface ReceivedNotification {
  id: string
  docId: string
  doc: string
  version: string
  time: string
  from: string
  unread: boolean
  overdue: boolean
  summary: string[]
  targetTeams: string[]
}

export interface SentChange {
  id: string
  docId: string
  doc: string
  version: string
  time: string
  status: '확인 진행' | '확인 완료'
  summary: string[]
  targetTeams: TeamCheck[]
}

export const notificationQueries = {
  confirmedChanges: () =>
    queryOptions({
      queryKey: ['changes', 'confirmed'],
      queryFn: () => request<ConfirmedChange[]>('/changes?status=confirmed'),
    }),
  received: () =>
    queryOptions({
      queryKey: ['notifications', 'received'],
      queryFn: () => request<ReceivedNotification[]>('/notifications'),
    }),
  sent: () =>
    queryOptions({
      queryKey: ['notifications', 'sent'],
      queryFn: () => request<SentChange[]>('/notifications/sent'),
    }),
}

export function respondToNotification(id: string, response: TeamResponse) {
  return request<void>(`/notifications/${id}/response`, {
    method: 'POST',
    body: JSON.stringify({ response }),
  })
}
