import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'

import { documentQueries, uploadDocument } from '../../api/documents'
import {
  createSubmission,
  requestApproval,
  submissionQueries,
  type ApprovalRequestBody,
  type SubmissionMode,
} from '../../api/submissions'
import { useCurrentUser } from '../../hooks/useAuth'
import AnalyzingStep from './AnalyzingStep'
import ReviewStep from './ReviewStep'
import UploadStep from './UploadStep'

const STEPS = ['업로드', '변경 분석', '영향 팀 확인', '승인 요청']

const STEP_BADGE = {
  done: 'border-accent-500/40 bg-accent-500/15 text-accent-300',
  active: 'border-primary-500 bg-primary-500 text-background-950 shadow-glow',
  idle: 'border-background-600 text-foreground-500',
}

function Stepper({ current }: { current: number }) {
  return (
    <section className="panel flex flex-wrap items-center gap-2 p-2 md:gap-3 md:p-3">
      {STEPS.map((label, i) => {
        const state = i < current ? 'done' : i === current ? 'active' : 'idle'
        return (
          <div key={label} className="flex flex-1 items-center gap-2">
            <span
              className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border font-label text-[11px] ${STEP_BADGE[state]}`}
            >
              {state === 'done' ? <i className="ri-check-line text-[13px]" /> : i + 1}
            </span>
            <span
              className={`whitespace-nowrap font-label text-[12px] ${state === 'idle' ? 'text-foreground-500' : 'text-foreground-100'}`}
            >
              {label}
            </span>
            {i < STEPS.length - 1 && <span className="h-px flex-1 bg-background-700/80" />}
          </div>
        )
      })}
    </section>
  )
}

function SubmitPage() {
  const { user, project, teamName } = useCurrentUser()
  const [file, setFile] = useState<File | null>(null)
  const [mode, setMode] = useState<SubmissionMode>('existing')
  const [documentId, setDocumentId] = useState<string | null>(null)
  const [submissionId, setSubmissionId] = useState<string | null>(null)
  const [approvalSent, setApprovalSent] = useState<{ teamCount: number } | null>(null)

  const { data: documents = [] } = useQuery(documentQueries.list())
  // 새 버전은 내 팀 문서에만 올릴 수 있다
  const teamDocuments = documents.filter((d) => d.team === teamName)
  const selectedMode = teamDocuments.length === 0 ? 'new' : mode
  const selectedDoc =
    selectedMode === 'existing'
      ? (teamDocuments.find((d) => d.id === documentId) ?? teamDocuments[0])
      : undefined

  const create = useMutation({
    mutationFn: async (target: File) => {
      const uploaded = await uploadDocument(target, user.user_id, project.project_id)
      return createSubmission({
        fileName: uploaded.original_filename,
        storedFilename: uploaded.stored_filename,
        mode: selectedMode,
        documentId: selectedDoc?.id ?? null,
        baseVersion: selectedDoc ? `v${selectedDoc.version}` : null,
      })
    },
    onSuccess: ({ id }) => setSubmissionId(id),
  })

  const { data: analysis } = useQuery({
    ...submissionQueries.analysis(submissionId ?? ''),
    enabled: !!submissionId,
  })

  const approval = useMutation({
    mutationFn: (body: ApprovalRequestBody) => requestApproval(submissionId!, body),
    onSuccess: (_, body) => setApprovalSent({ teamCount: body.teams.length }),
  })

  const restart = () => {
    setSubmissionId(null)
    setApprovalSent(null)
    create.reset()
  }

  const analysisDone = analysis?.status === 'completed' && !!analysis.result
  const currentStep = approvalSent ? 3 : analysisDone ? 2 : submissionId ? 1 : 0

  return (
    <div className="space-y-6 pb-16">
      <section>
        <p className="overline">{project.name} · 변경 제출</p>
        <h1 className="mt-3 font-heading text-[28px] leading-tight text-foreground-50 md:text-[34px]">
          <span className="font-semibold">변경</span>{' '}
          <span className="font-light text-foreground-200">제출</span>
        </h1>
        <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-foreground-400">
          팀 안 작업은 원래 쓰던 도구에서 그대로 하고, 확정하려는 산출물만 여기에 한 번 올립니다.
          승인 전 제출본은 제출자·승인자·같은 팀만 볼 수 있습니다.
        </p>
      </section>

      <Stepper current={currentStep} />

      {currentStep === 0 && (
        <UploadStep
          file={file}
          mode={selectedMode}
          teamDocuments={teamDocuments}
          selectedDoc={selectedDoc}
          submitting={create.isPending}
          error={create.error?.message ?? ''}
          onFileChange={setFile}
          onModeChange={setMode}
          onDocumentChange={setDocumentId}
          onStart={() => file && create.mutate(file)}
        />
      )}

      {currentStep === 1 && (
        <AnalyzingStep
          fileName={file?.name ?? ''}
          compareLabel={
            selectedDoc ? `HEAD v${selectedDoc.version}와 비교` : '새 문서 · HEAD 비교 없음'
          }
          analysis={analysis}
          onRetry={restart}
        />
      )}

      {currentStep === 2 && analysis?.result && (
        <ReviewStep
          result={analysis.result}
          submitting={approval.isPending}
          onBack={restart}
          onRequestApproval={(body) => approval.mutate(body)}
        />
      )}

      {currentStep === 3 && (
        <section className="panel mx-auto max-w-xl p-6 text-center md:p-8">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full border border-accent-500/40 text-accent-300">
            <i className="ri-checkbox-circle-line text-xl" />
          </span>
          <h2 className="mt-4 font-heading text-[19px] text-foreground-50">
            승인 요청을 보냈습니다
          </h2>
          <p className="mt-1.5 text-[13px] leading-relaxed text-foreground-400">
            {selectedDoc ? `${selectedDoc.name} v${selectedDoc.version + 1}` : file?.name} · 알림
            대상 {approvalSent?.teamCount}팀 · 승인자에게 알림이 갔습니다. 승인되면 검증된 3줄
            요약이 팀에 발송됩니다.
          </p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            <Link
              to={selectedDoc ? `/documents/${selectedDoc.id}` : '/documents'}
              className="flex h-9 cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-md bg-foreground-50 px-4 text-[13px] font-medium text-background-950 transition hover:bg-foreground-100"
            >
              검토 화면 보기 <i className="ri-arrow-right-line text-[13px]" />
            </Link>
            <button
              type="button"
              onClick={restart}
              className="flex h-9 cursor-pointer items-center whitespace-nowrap rounded-md border border-background-600/80 px-4 text-[13px] text-foreground-200 transition hover:bg-background-800/60"
            >
              다른 파일 제출
            </button>
          </div>
        </section>
      )}
    </div>
  )
}

export default SubmitPage
