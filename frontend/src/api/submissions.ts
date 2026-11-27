import { queryOptions } from '@tanstack/react-query'

import { request } from './client'
import type { ParagraphDiff } from './documents'

export type SubmissionMode = 'existing' | 'new'

export interface CreateSubmissionBody {
  fileName: string
  storedFilename: string
  mode: SubmissionMode
  // 기존 문서의 새 버전일 때만 (새 문서는 HEAD 비교 없음)
  documentId: string | null
  baseVersion: string | null
}

export interface ImpactCandidate {
  name: string
  checked: boolean
  confidence: '높음' | '보통' | '낮음'
  reason: string
}

export interface AnalysisStep {
  label: string
  detail: string
}

export interface AnalysisResult {
  paragraphs: ParagraphDiff[]
  summary: string[]
  impactTeams: ImpactCandidate[]
  approvers: string
}

export interface SubmissionAnalysis {
  id: string
  fileName: string
  status: 'analyzing' | 'completed' | 'failed'
  steps: AnalysisStep[]
  completedSteps: number
  result: AnalysisResult | null
}

export interface ApprovalRequestBody {
  teams: string[]
  excludeReason: string
  summaryOverride: string
}

export function createSubmission(body: CreateSubmissionBody) {
  return request<{ id: string }>('/submissions', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function requestApproval(submissionId: string, body: ApprovalRequestBody) {
  return request<void>(`/submissions/${submissionId}/approval-request`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

// 분석은 Celery 워커에서 비동기로 돌기 때문에 완료·실패 전까지 폴링한다
export const submissionQueries = {
  analysis: (submissionId: string) =>
    queryOptions({
      queryKey: ['submissions', submissionId, 'analysis'],
      queryFn: () => request<SubmissionAnalysis>(`/submissions/${submissionId}/analysis`),
      refetchInterval: (query) => (query.state.data?.status === 'analyzing' ? 900 : false),
    }),
}
