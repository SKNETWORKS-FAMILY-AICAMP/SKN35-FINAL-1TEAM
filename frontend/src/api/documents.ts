import { queryOptions } from '@tanstack/react-query'

import { request } from './client'

export type Scope = '사내 공개' | '프로젝트 내부' | '팀 내부' | '외부 공유'
export type FileExt = 'DOCX' | 'PPTX' | 'XLSX' | 'MD' | 'PDF' | 'HWPX' | 'TXT'

// backend/app/pipeline/models.py 의 Location 과 같은 모양
export interface Location {
  page?: number | null
  slide?: number | null
  sheet?: string | null
  row?: number | null
  index?: number | null
}

export type DiffType = 'unchanged' | 'added' | 'removed' | 'modified'

export interface ParagraphDiff {
  id: string
  type: DiffType
  before: string | null
  after: string | null
  author: string | null
  version: string | null
  location: Location
}

export type TeamResponse = '확인 완료' | '영향 없음'

export interface ImpactTeamStatus {
  name: string
  reason: string
  confidence: '높음' | '보통' | '낮음'
  state: 'pending' | 'done'
  by: string
  response: TeamResponse | null
}

export interface ChangeItem {
  paragraphId: string
  type: '추가' | '삭제' | '수정'
  label: string
}

export interface DocumentSummary {
  id: string
  name: string
  team: string
  owner: string
  version: number
  scope: Scope
  updatedAt: string
  changes: number
  pending: boolean
  summary: string
  ext: FileExt
  size: string
}

export interface DocumentReview {
  id: string
  name: string
  team: string
  owner: string
  submitter: string
  fileName: string
  headVersion: string
  candidateVersion: string
  baseVersion: string
  submittedAt: string
  scope: Scope
  ext: FileExt
  size: string
  lines: number
  summary: string[]
  verification: { passed: boolean; rewrites: number; checkedAt: string; agent: string }
  overwrite: { count: number; message: string }
  parser: { engine: string; paragraphCount: number }
  paragraphs: ParagraphDiff[]
  changeItems: ChangeItem[]
  teams: ImpactTeamStatus[]
}

export const documentQueries = {
  list: () =>
    queryOptions({
      queryKey: ['documents'],
      queryFn: () => request<DocumentSummary[]>('/documents'),
    }),
  review: (docId: string) =>
    queryOptions({
      queryKey: ['documents', docId, 'review'],
      queryFn: () => request<DocumentReview>(`/documents/${docId}/review`),
    }),
}

export function approveDocument(docId: string) {
  return request<void>(`/documents/${docId}/approve`, { method: 'POST' })
}

export function rejectDocument(docId: string, reason: string) {
  return request<void>(`/documents/${docId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })
}

export function respondToChange(docId: string, team: string, response: TeamResponse) {
  return request<void>(`/documents/${docId}/responses`, {
    method: 'POST',
    body: JSON.stringify({ team, response }),
  })
}

// backend/app/documents/schemas.py 의 DocumentUploadResponse
export interface DocumentUploadResponse {
  original_filename: string
  stored_filename: string
  file_path: string
  file_size: number
  user_id: number
  project_id: number
}

export function uploadDocument(file: File, userId: number, projectId: number) {
  const form = new FormData()
  form.append('file', file)
  form.append('user_id', String(userId))
  form.append('project_id', String(projectId))
  return request<DocumentUploadResponse>('/documents/upload-document', {
    method: 'POST',
    body: form,
  })
}
