import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'

import { authQueries, login, logout, type LoginRequest } from '../api/auth'
import { tokenStorage } from '../api/client'
import { projectQueries, type Project, type ProjectMemberRole } from '../api/project'

const PROJECT_KEY = 'currentProjectId'

const ROLE_LABEL: Record<ProjectMemberRole, string> = {
  OWNER: '오너',
  LEADER: '팀장',
  MEMBER: '팀원',
}

function pickProject(projects: Project[]) {
  const savedId = Number(localStorage.getItem(PROJECT_KEY))
  return (
    projects.find((p) => p.project_id === savedId) ??
    projects.find((p) => p.status === 'START') ??
    projects[0]
  )
}

// 로그인 사용자 · 현재 프로젝트 · 내 팀을 한 번에 불러온다. AppLayout 이 이 결과로 화면을 막는다
export function useSession() {
  const hasToken = !!tokenStorage.get()
  const me = useQuery({ ...authQueries.me(), enabled: hasToken })
  const projects = useQuery({ ...projectQueries.list(), enabled: me.isSuccess })
  const project = projects.data && pickProject(projects.data)
  const detail = useQuery({
    ...projectQueries.detail(project?.project_id ?? 0),
    enabled: !!project,
  })
  const teams = useQuery({
    ...projectQueries.teams(project?.project_id ?? 0),
    enabled: !!project,
  })

  return {
    unauthenticated: !hasToken || me.isError,
    noProject: projects.isSuccess && !project,
    ready: me.isSuccess && detail.isSuccess && teams.isSuccess,
  }
}

// AppLayout 안에서만 쓴다 (useSession 이 불러온 캐시를 읽는다)
export function useCurrentUser() {
  const { data: user } = useQuery(authQueries.me())
  const { data: projects = [] } = useQuery(projectQueries.list())
  const projectId = pickProject(projects)?.project_id ?? 0
  const { data: project } = useQuery(projectQueries.detail(projectId))
  const { data: teams = [] } = useQuery(projectQueries.teams(projectId))

  if (!user || !project) throw new Error('useCurrentUser must be used inside AppLayout')

  const team = teams.find((t) => t.project_team_id === project.my_project_team_id)
  const canApprove = project.my_is_approval === 'Y'

  return {
    user,
    project,
    projects,
    teams,
    teamName: team?.name ?? '소속 팀 없음',
    roleLabel: canApprove ? '승인권자' : ROLE_LABEL[project.my_role],
    // 화면 노출 기준. 실제 권한 판정은 백엔드가 한다
    can: {
      approve: canApprove,
      respond: !!team,
    },
  }
}

export function useSelectProject() {
  const queryClient = useQueryClient()

  return (projectId: number) => {
    localStorage.setItem(PROJECT_KEY, String(projectId))
    // 프로젝트별 데이터를 새로 받는다
    queryClient.invalidateQueries({ predicate: (q) => q.queryKey[0] !== 'me' })
  }
}

export function useLogin() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: LoginRequest) => login(body),
    onSuccess: ({ access_token }) => {
      // 이전 사용자의 캐시가 남지 않도록 비운다
      queryClient.clear()
      tokenStorage.set(access_token)
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return () => {
    logout().catch(() => undefined)
    tokenStorage.clear()
    queryClient.clear()
    navigate('/login', { replace: true })
  }
}
