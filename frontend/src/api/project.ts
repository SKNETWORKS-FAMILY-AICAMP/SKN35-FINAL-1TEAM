import { queryOptions } from '@tanstack/react-query'

import { request } from './client'

export type ProjectStatus = 'START' | 'END'
export type ProjectMemberRole = 'OWNER' | 'LEADER' | 'MEMBER'
export type YN = 'Y' | 'N'

export const PROJECT_STATUS_LABEL: Record<ProjectStatus, string> = {
  START: '진행 중',
  END: '종료',
}

// '2026-09-01T00:00:00' → '2026.09.01'
export const formatDate = (iso: string) => iso.slice(0, 10).replaceAll('-', '.')

// backend/app/projects/schemas.py
export interface Project {
  project_id: number
  name: string
  status: ProjectStatus
  created_at: string
  my_role: ProjectMemberRole
}

export interface ProjectDetail extends Project {
  updated_at: string
  my_is_approval: YN
  my_project_team_id: number | null
}

export interface ProjectTeam {
  project_team_id: number
  project_id: number
  name: string | null
  team_leader: number | null
  team_leader_name: string | null
  member_count: number
}

export interface ProjectMember {
  project_member_id: number
  project_team_id: number
  user_id: number
  name: string
  email: string
  role: ProjectMemberRole
  is_approval: YN
}

// 아래 두 타입은 백엔드 미구현 (MSW 목업)
export interface ProjectMetric {
  key: 'headDocuments' | 'pendingApprovals' | 'unreadAlerts' | 'confirmRate'
  label: string
  value: string
  unit: string
  hint: string
}

export interface PendingApproval {
  id: string
  docId: string
  doc: string
  version: string
  submitter: string
  team: string
  time: string
}

// 프로젝트·팀 정보는 자주 바뀌지 않아 화면 이동마다 다시 받지 않는다
const PROJECT_STALE_TIME = 5 * 60 * 1000

export const projectQueries = {
  list: () =>
    queryOptions({
      queryKey: ['projects'],
      queryFn: () => request<{ projects: Project[] }>('/projects'),
      staleTime: PROJECT_STALE_TIME,
      select: (data) => data.projects,
    }),
  detail: (projectId: number) =>
    queryOptions({
      queryKey: ['projects', projectId],
      queryFn: () => request<ProjectDetail>(`/projects/${projectId}`),
      staleTime: PROJECT_STALE_TIME,
    }),
  teams: (projectId: number) =>
    queryOptions({
      queryKey: ['projects', projectId, 'teams'],
      queryFn: () => request<{ teams: ProjectTeam[] }>(`/projects/${projectId}/teams`),
      staleTime: PROJECT_STALE_TIME,
      select: (data) => data.teams,
    }),
  metrics: (projectId: number) =>
    queryOptions({
      queryKey: ['projects', projectId, 'metrics'],
      queryFn: () => request<ProjectMetric[]>(`/projects/${projectId}/metrics`),
    }),
  pendingApprovals: (projectId: number) =>
    queryOptions({
      queryKey: ['projects', projectId, 'approvals', 'pending'],
      queryFn: () => request<PendingApproval[]>(`/projects/${projectId}/approvals?status=pending`),
    }),
}
