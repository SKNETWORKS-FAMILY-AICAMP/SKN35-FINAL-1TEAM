import { delay, http, HttpResponse } from 'msw'

import type { LoginRequest } from '../api/auth'
import type { TeamResponse } from '../api/documents'
import type { CreateSubmissionBody, SubmissionAnalysis } from '../api/submissions'
import {
  accounts,
  analysisSteps,
  assistantFallback,
  assistantKnowledge,
  company,
  confirmedChanges,
  departments,
  documentReview,
  documents,
  impactCandidates,
  metrics,
  pendingApprovals,
  projectMembers,
  projects,
  projectTeams,
  receivedNotifications,
  reviewParagraphs,
  sentChanges,
} from './data'

const API = '/api/v1'
const STEP_MS = 900
const HEAD_DIFF_STEP = 'HEAD 차이 검사'

const unauthorized = () => HttpResponse.json({ detail: '로그인이 필요합니다.' }, { status: 401 })
const forbidden = () => HttpResponse.json({ detail: '권한이 없습니다.' }, { status: 403 })
const notFound = () => HttpResponse.json({ detail: '데이터를 찾을 수 없습니다.' }, { status: 404 })
const noContent = () => new HttpResponse(null, { status: 204 })

// 실제 백엔드처럼 sub 에 user_id 를 담은 JWT 모양 토큰
function createMockToken(userId: number) {
  const encode = (value: object) => btoa(JSON.stringify(value)).replace(/=+$/, '')
  return `${encode({ alg: 'none', typ: 'JWT' })}.${encode({ sub: String(userId), type: 'access' })}.mock`
}

function getUserId(request: Request) {
  const token = request.headers.get('Authorization')?.replace('Bearer ', '')
  if (!token) return null
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    return Number((JSON.parse(atob(payload)) as { sub: string }).sub)
  } catch {
    return null
  }
}

// 목업 계정이면 쇼핑몰 구축 프로젝트의 소속 정보를, 실제 백엔드 계정이면 null 을 돌려준다
// (부분 목업 모드에서는 실제 계정으로 들어오므로 권한·필터 검사를 건너뛴다)
function getMockMember(request: Request) {
  const userId = getUserId(request)
  const account = accounts.find((a) => a.user_id === userId)
  const member = projectMembers.find((m) => m.user_id === userId && m.project_id === 1)
  if (!account || !member) return null
  const team = projectTeams.find((t) => t.project_team_id === member.project_team_id)
  return { ...member, name: account.name, team: team?.name ?? '' }
}

function membersOf(projectId: number) {
  return projectMembers
    .filter((m) => m.project_id === projectId)
    .map((m) => {
      const account = accounts.find((a) => a.user_id === m.user_id)!
      return {
        project_member_id: m.project_member_id,
        project_team_id: m.project_team_id,
        user_id: m.user_id,
        name: account.name,
        email: account.email,
        role: m.role,
        is_approval: m.is_approval,
      }
    })
}

function findProjectForUser(projectId: number, userId: number | null) {
  const project = projects.find((p) => p.project_id === projectId)
  const member = projectMembers.find((m) => m.project_id === projectId && m.user_id === userId)
  return project && member ? { project, member } : null
}

const submissions = new Map<
  string,
  { fileName: string; mode: CreateSubmissionBody['mode']; startedAt: number }
>()

function toAnalysis(id: string): SubmissionAnalysis {
  const { fileName, mode, startedAt } = submissions.get(id)!
  // 새 문서는 HEAD 와 비교하지 않는다
  const steps =
    mode === 'new' ? analysisSteps.filter((s) => s.label !== HEAD_DIFF_STEP) : analysisSteps
  const elapsed = Date.now() - startedAt
  const completedSteps = Math.min(steps.length, Math.floor(elapsed / STEP_MS))
  const finished = elapsed >= (steps.length + 1) * STEP_MS
  const approvers = membersOf(1)
    .filter((m) => m.is_approval === 'Y')
    .map((m) => m.name)
  const changed = reviewParagraphs.filter((p) => p.type !== 'unchanged')

  return {
    id,
    fileName,
    status: finished ? 'completed' : 'analyzing',
    steps,
    completedSteps,
    result: finished
      ? {
          paragraphs:
            mode === 'new'
              ? changed.map((p) => ({ ...p, type: 'added' as const, before: null }))
              : changed,
          summary: documentReview.summary,
          impactTeams: impactCandidates,
          approvers: approvers.join(', '),
        }
      : null,
  }
}

// 백엔드에 이미 구현된 API 의 목업. 백엔드를 띄우지 않고 개발할 때만 쓴다
export const implementedHandlers = [
  http.post<never, LoginRequest>(`${API}/auth/login`, async ({ request }) => {
    const { email, password } = await request.json()
    const account = accounts.find(
      (a) => a.email === email.trim().toLowerCase() && a.password === password,
    )
    if (!account) {
      return HttpResponse.json(
        { detail: '이메일 또는 비밀번호가 올바르지 않습니다.' },
        { status: 401 },
      )
    }
    return HttpResponse.json({
      access_token: createMockToken(account.user_id),
      token_type: 'bearer',
    })
  }),
  // 목업에는 refresh 쿠키가 없으므로 항상 재로그인
  http.post(`${API}/auth/refresh`, unauthorized),
  http.post(`${API}/auth/logout`, noContent),

  http.get(`${API}/companies`, () => HttpResponse.json(company)),
  http.get(`${API}/companies/users`, ({ request }) => {
    if (!getUserId(request)) return unauthorized()
    const users = accounts.map((a) => ({
      user_id: a.user_id,
      dept_id: a.dept_id,
      name: a.name,
      email: a.email,
      user_type: a.user_type,
    }))
    return HttpResponse.json({ users })
  }),
  http.get(`${API}/companies/departments`, () => HttpResponse.json({ departments })),

  http.get(`${API}/projects`, ({ request }) => {
    const userId = getUserId(request)
    if (!userId) return unauthorized()
    const mine = projectMembers
      .filter((m) => m.user_id === userId)
      .map((m) => ({
        ...projects.find((p) => p.project_id === m.project_id)!,
        my_role: m.role,
      }))
    return HttpResponse.json({ projects: mine })
  }),
  http.get<{ projectId: string }>(`${API}/projects/:projectId`, ({ params, request }) => {
    const found = findProjectForUser(Number(params.projectId), getUserId(request))
    if (!found) return forbidden()
    return HttpResponse.json({
      ...found.project,
      updated_at: found.project.created_at,
      my_role: found.member.role,
      my_is_approval: found.member.is_approval,
      my_project_team_id: found.member.project_team_id,
    })
  }),
  http.get<{ projectId: string }>(`${API}/projects/:projectId/teams`, ({ params, request }) => {
    const projectId = Number(params.projectId)
    if (!findProjectForUser(projectId, getUserId(request))) return forbidden()
    const members = membersOf(projectId)
    const teams = projectTeams
      .filter((t) => t.project_id === projectId)
      .map((t) => {
        const leader = members.find(
          (m) => m.project_team_id === t.project_team_id && m.role === 'LEADER',
        )
        return {
          ...t,
          team_leader: leader?.user_id ?? null,
          team_leader_name: leader?.name ?? null,
          member_count: members.filter((m) => m.project_team_id === t.project_team_id).length,
        }
      })
    return HttpResponse.json({ teams })
  }),
  http.get<{ projectId: string }>(`${API}/projects/:projectId/members`, ({ params, request }) => {
    const projectId = Number(params.projectId)
    if (!findProjectForUser(projectId, getUserId(request))) return forbidden()
    return HttpResponse.json({ members: membersOf(projectId) })
  }),

  http.post(`${API}/documents/upload-document`, async ({ request }) => {
    const form = await request.formData()
    const file = form.get('file')
    if (!(file instanceof File)) {
      return HttpResponse.json({ detail: '파일명이 존재하지 않습니다.' }, { status: 400 })
    }
    const dot = file.name.lastIndexOf('.')
    const storedFilename = `${file.name.slice(0, dot)}_${Date.now()}${file.name.slice(dot)}`
    await delay(400)
    return HttpResponse.json(
      {
        original_filename: file.name,
        stored_filename: storedFilename,
        file_path: `storage/temp/${storedFilename}`,
        file_size: file.size,
        user_id: Number(form.get('user_id')),
        project_id: Number(form.get('project_id')),
      },
      { status: 201 },
    )
  }),
]

// 백엔드에 아직 없는 API 의 목업
export const pendingHandlers = [
  http.get(`${API}/projects/:projectId/metrics`, () => HttpResponse.json(metrics)),
  http.get(`${API}/projects/:projectId/approvals`, () => HttpResponse.json(pendingApprovals)),

  http.get(`${API}/documents`, () => HttpResponse.json(documents)),
  // 상세 목업은 요구사항정의서 한 건만 있어 모든 문서에 같은 검토 데이터를 돌려준다
  http.get(`${API}/documents/:docId/review`, () => HttpResponse.json(documentReview)),
  http.post(`${API}/documents/:docId/approve`, async ({ request }) => {
    const member = getMockMember(request)
    // 승인권자만, 본인 제출 건은 승인 불가
    if (member && (member.is_approval !== 'Y' || member.name === documentReview.submitter)) {
      return forbidden()
    }
    await delay(300)
    return noContent()
  }),
  http.post<never, { reason: string }>(`${API}/documents/:docId/reject`, async ({ request }) => {
    const member = getMockMember(request)
    if (member && (member.is_approval !== 'Y' || member.name === documentReview.submitter)) {
      return forbidden()
    }
    const { reason } = await request.json()
    if (!reason?.trim()) {
      return HttpResponse.json({ detail: '반려 사유를 입력해 주세요.' }, { status: 400 })
    }
    return noContent()
  }),
  http.post<never, { team: string; response: TeamResponse }>(
    `${API}/documents/:docId/responses`,
    async ({ request }) => {
      const member = getMockMember(request)
      const { team, response } = await request.json()
      // 자기 팀 응답만 남길 수 있다
      if (member && member.team !== team) return forbidden()
      documentReview.teams = documentReview.teams.map((t) =>
        t.name === team ? { ...t, state: 'done', by: member?.name ?? '', response } : t,
      )
      return noContent()
    },
  ),

  http.get(`${API}/changes`, () => HttpResponse.json(confirmedChanges)),
  http.get(`${API}/notifications`, ({ request }) => {
    const member = getMockMember(request)
    return HttpResponse.json(
      member
        ? receivedNotifications.filter((n) => n.targetTeams.includes(member.team))
        : receivedNotifications,
    )
  }),
  http.get(`${API}/notifications/sent`, ({ request }) => {
    const member = getMockMember(request)
    // 목업의 보낸 변경은 모두 홍길동이 제출한 건
    return HttpResponse.json(!member || member.name === '홍길동' ? sentChanges : [])
  }),
  http.post<{ id: string }>(`${API}/notifications/:id/response`, ({ params, request }) => {
    const member = getMockMember(request)
    const target = receivedNotifications.find((n) => n.id === params.id)
    if (!target) return notFound()
    if (member && !target.targetTeams.includes(member.team)) return forbidden()
    target.unread = false
    return noContent()
  }),

  http.post<never, CreateSubmissionBody>(`${API}/submissions`, async ({ request }) => {
    const member = getMockMember(request)
    const { fileName, mode, documentId } = await request.json()
    // 새 버전은 자기 팀 문서에만
    const doc = documents.find((d) => d.id === documentId)
    if (mode === 'existing' && (!doc || (member && doc.team !== member.team))) return forbidden()
    const id = `sub-${Date.now()}`
    submissions.set(id, { fileName, mode, startedAt: Date.now() })
    return HttpResponse.json({ id }, { status: 201 })
  }),
  http.get<{ id: string }>(`${API}/submissions/:id/analysis`, ({ params }) => {
    if (!submissions.has(params.id)) return notFound()
    return HttpResponse.json(toAnalysis(params.id))
  }),
  http.post(`${API}/submissions/:id/approval-request`, async () => {
    await delay(300)
    return noContent()
  }),

  http.post<never, { question: string }>(`${API}/assistant/ask`, async ({ request }) => {
    const { question } = await request.json()
    await delay(650)
    const matched = assistantKnowledge.find((k) => k.keywords.some((w) => question.includes(w)))
    return HttpResponse.json(matched?.answer ?? assistantFallback)
  }),
]
