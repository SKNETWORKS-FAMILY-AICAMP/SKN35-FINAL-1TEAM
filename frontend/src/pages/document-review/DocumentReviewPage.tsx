import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router'

import { documentQueries } from '../../api/documents'
import DiffView, { type DiffMode } from '../../components/DiffView'
import Toast from '../../components/Toast'
import { useCurrentUser } from '../../hooks/useAuth'
import { useToast } from '../../hooks/useToast'
import ApprovalPanel, { type ApprovalStatus } from './ApprovalPanel'
import OwnerResponsePanel from './OwnerResponsePanel'
import ReviewSidebar from './ReviewSidebar'

const DIFF_MODES: { key: DiffMode; label: string }[] = [
  { key: 'split', label: '나란히' },
  { key: 'unified', label: '통합' },
]

function Divider({ height = 'h-2.5' }: { height?: string }) {
  return <span className={`${height} w-px bg-background-600`} />
}

function DocumentReviewPage() {
  const { docId = '' } = useParams()
  const { user, teamName, can } = useCurrentUser()
  const toast = useToast()

  const [mode, setMode] = useState<DiffMode>('split')
  const [showOverwrite, setShowOverwrite] = useState(false)
  const [approvalStatus, setApprovalStatus] = useState<ApprovalStatus>('pending')

  const { data: review } = useQuery(documentQueries.review(docId))

  if (!review) return null

  return (
    <div className="space-y-5 pb-16">
      <div className="flex items-center gap-2 text-[12.5px] text-foreground-500">
        <Link to="/documents" className="cursor-pointer transition hover:text-primary-300">
          기준 문서
        </Link>
        <i className="ri-arrow-right-s-line text-[13px]" />
        <span className="text-foreground-300">{review.name}</span>
        <Divider height="h-3" />
        <span>
          {review.team} · {review.scope}
        </span>
      </div>

      <section className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="font-heading text-[26px] leading-tight text-foreground-50 md:text-[32px]">
              {review.name}
            </h1>
            <span className="flex items-center gap-1 font-label text-[12px]">
              <span className="rounded-sm border border-background-600 bg-background-800/70 px-1.5 py-0.5 text-foreground-300">
                HEAD {review.headVersion}
              </span>
              <i className="ri-arrow-right-line text-[11px] text-foreground-600" />
              <span className="rounded-sm border border-primary-500/30 px-1.5 py-0.5 text-primary-300">
                {review.candidateVersion} 검토 중
              </span>
            </span>
          </div>
          <p className="mt-2 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[12.5px] text-foreground-500">
            <span className="flex items-center gap-1">
              <i className="ri-user-line text-[13px]" /> {review.owner} · {review.team}
            </span>
            <Divider />
            <span>제출 {review.submittedAt}</span>
            <Divider />
            <span>기준 버전 {review.baseVersion}</span>
            <Divider />
            <span>
              {review.ext} · {review.size} · {review.lines}줄
            </span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex h-9 items-center rounded-md border border-background-600/70 bg-background-900/60 p-1">
            {DIFF_MODES.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => setMode(item.key)}
                className={`h-7 cursor-pointer whitespace-nowrap rounded-full px-3 font-label text-[12px] transition ${mode === item.key ? 'bg-foreground-50 text-background-950' : 'text-foreground-400 hover:text-foreground-100'}`}
              >
                {item.label}
              </button>
            ))}
          </div>
          {/* TODO: 원본 다운로드 API 연결 (기준 버전 기록) */}
          <button
            type="button"
            onClick={() => toast.show('원본 파일 다운로드를 시작했습니다. 기준 버전이 기록됩니다.')}
            className="flex h-9 cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-md border border-background-600/80 px-3 text-[13px] text-foreground-200 transition hover:border-background-500 hover:bg-background-800/60"
          >
            <i className="ri-download-2-line text-[15px]" /> 원본 다운로드
          </button>
        </div>
      </section>

      <section className="panel flex flex-wrap items-center justify-between gap-3 p-3.5">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-sm border border-background-600/70 bg-background-800/60 text-[15px] text-foreground-400">
            <i className="ri-flask-line" />
          </span>
          <div>
            <p className="text-[13.5px] text-foreground-100">덮어쓰기 예시 보기</p>
            <p className="mt-0.5 text-[11.5px] text-foreground-500">
              켜면 HEAD 덮어쓰기 경고가 표시되고, 끄면 경고 없는 정상 승인 화면으로 돌아갑니다.
            </p>
          </div>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={showOverwrite}
          aria-label="덮어쓰기 예시 보기"
          onClick={() => setShowOverwrite((v) => !v)}
          className={`relative flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border px-0.5 transition ${showOverwrite ? 'border-amber-400/60 bg-amber-400/25' : 'border-background-600/80 bg-background-800/70'}`}
        >
          <span
            className={`h-[18px] w-[18px] rounded-full transition-all ${showOverwrite ? 'ml-auto bg-amber-300' : 'bg-foreground-500'}`}
          />
        </button>
      </section>

      {showOverwrite && (
        <div className="rounded-lg border border-amber-400/25 bg-amber-400/[0.06] p-3.5">
          <p className="flex items-start gap-1.5 text-[13px] leading-relaxed text-amber-200">
            <i className="ri-alert-line mt-0.5 text-[15px]" />
            {review.overwrite.message}
          </p>
          <p className="mt-2 text-[11.5px] leading-relaxed text-foreground-500">
            이 파일을 그대로 반영하면 먼저 반영된 FR-015 변경이 사라집니다. 제출자에게 병합을
            요청하세요.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
        <section className="panel p-3 md:p-4">
          <DiffView
            mode={mode}
            oldLabel={`이전 ${review.headVersion}`}
            newLabel={`${review.candidateVersion} · 검토 중`}
            paragraphs={review.paragraphs}
          />
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-background-700/60 pt-3 text-[12px] text-foreground-500">
            <i className="ri-information-line text-[13px]" />
            텍스트 문단만 비교합니다. 서식과 문서 안 이미지 변경은 추적하지 않습니다.
            <span className="ml-auto font-label uppercase tracking-[0.14em] text-foreground-600">
              {review.parser.engine} 파싱 · 문단 {review.parser.paragraphCount}개
            </span>
          </div>
        </section>

        <ReviewSidebar
          review={review}
          approvalStatus={approvalStatus}
          onResetApproval={() => setApprovalStatus('pending')}
        />
      </div>

      {can.respond && review.teams.some((t) => t.name === teamName) && (
        <OwnerResponsePanel review={review} team={teamName} onNotify={toast.show} />
      )}

      {/* 승인자는 본인이 제출한 건을 승인할 수 없다 */}
      {can.approve && review.submitter !== user.name && (
        <ApprovalPanel
          review={review}
          status={approvalStatus}
          showOverwrite={showOverwrite}
          onStatusChange={setApprovalStatus}
          onNotify={toast.show}
        />
      )}

      <Toast message={toast.message} />
    </div>
  )
}

export default DocumentReviewPage
