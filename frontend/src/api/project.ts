import { queryOptions } from '@tanstack/react-query'

import { request } from './client'

export type ProjectStatus = 'START' | 'END'
export type ProjectMemberRole = 'OWNER' | 'LEADER' | 'MEMBER'
export type YN = 'Y' | 'N'

export const PROJECT_STATUS_LABEL: Record<ProjectStatus, string> = {
  START: '진행 중',
  END: '종료',
}

export const PROJECT_ROLE_LABEL: Record<ProjectMemberRole, string> = {
  OWNER: '오너',
  LEADER: '팀장',
  MEMBER: '팀원',
}

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

export interface ProjectTeamCreateRequest {
  name: string
  team_leader: number
  is_approval: YN
}

// OWNER 는 부여할 수 없고, 승인권자(is_approval=Y)는 LEADER 만 가능
export interface ProjectMemberCreateItem {
  user_id: number
  project_team_id: number
  role: Exclude<ProjectMemberRole, 'OWNER'>
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
  members: (projectId: number) =>
    queryOptions({
      queryKey: ['projects', projectId, 'members'],
      queryFn: () => request<{ members: ProjectMember[] }>(`/projects/${projectId}/members`),
      select: (data) => data.members,
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

// 프로젝트 생성: MANAGER·ADMIN 만 가능, 만든 사람이 OWNER
export function createProject(name: string) {
  return request<Omit<Project, 'my_role'>>('/projects', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

// 팀 생성: OWNER 만 가능, 대표 팀장을 그 팀의 LEADER 로 함께 등록
export function createProjectTeam(projectId: number, body: ProjectTeamCreateRequest) {
  return request<ProjectTeam>(`/projects/${projectId}/teams`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

// 멤버 일괄 추가: OWNER 는 모든 팀, LEADER 는 자기 팀에 MEMBER 만
export function addProjectMembers(projectId: number, members: ProjectMemberCreateItem[]) {
  return request<{ members: unknown[] }>(`/projects/${projectId}/members`, {
    method: 'POST',
    body: JSON.stringify({ members }),
  })
}

// 대표 팀장 변경: OWNER 만 가능, 그 팀의 LEADER 중에서만
export function updateTeamLeader(projectId: number, projectTeamId: number, teamLeader: number) {
  return request<ProjectTeam>(`/projects/${projectId}/teams/${projectTeamId}/leader`, {
    method: 'PATCH',
    body: JSON.stringify({ team_leader: teamLeader }),
  })
}
