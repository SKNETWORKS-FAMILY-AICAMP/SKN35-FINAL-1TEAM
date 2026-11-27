import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'

import { approveDocument, rejectDocument, type DocumentReview } from '../../api/documents'
import Badge from '../../components/Badge'

export type ApprovalStatus = 'pending' | 'approved' | 'rejected'

const REJECT_REASON_MAX = 500

interface ApprovalPanelProps {
  review: DocumentReview
  status: ApprovalStatus
  showOverwrite: boolean
  onStatusChange: (status: ApprovalStatus) => void
  onNotify: (message: string) => void
}

function ApprovalPanel({
  review,
  status,
  showOverwrite,
  onStatusChange,
  onNotify,
}: ApprovalPanelProps) {
  const [rejectOpen, setRejectOpen] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [reason, setReason] = useState('')

  const approve = useMutation({
    mutationFn: () => approveDocument(review.id),
    onSuccess: () => {
      onStatusChange('approved')
      setConfirmOpen(false)
      onNotify('승인 완료. 영향 팀에 알림을 발송했습니다.')
    },
  })

  const reject = useMutation({
    mutationFn: () => rejectDocument(review.id, reason),
    onSuccess: () => {
      onStatusChange('rejected')
      setRejectOpen(false)
      onNotify('반려 사유를 작성자에게 알렸습니다.')
    },
  })

  const handleReject = () => {
    // 반려 사유는 필수 (APV-06)
    if (!reason.trim()) {
      onNotify('반려 사유를 입력해 주세요.')
      return
    }
    reject.mutate()
  }

  return (
    <section className="panel p-5 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="font-heading text-[17px] font-medium text-foreground-50">승인 처리</h2>
          <p className="mt-1 text-[12.5px] text-foreground-500">
            승인권자로 처리합니다. 승인하면 {review.candidateVersion}이 HEAD가 되고 영향 팀에 요약이
            발송됩니다.
          </p>
        </div>
        <Badge tone="warning" icon="ri-checkbox-circle-line">
          승인권자
        </Badge>
      </div>

      {status === 'pending' && (
        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setConfirmOpen(true)}
            className="flex h-10 cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-md bg-primary-500 px-5 font-label text-[13.5px] font-semibold text-background-950 shadow-glow transition hover:bg-primary-400"
          >
            <i className="ri-check-line text-[15px]" /> 승인하기
          </button>
          <button
            type="button"
            onClick={() => setRejectOpen((open) => !open)}
            className="flex h-10 cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-md border border-background-600/80 px-5 font-label text-[13.5px] text-foreground-200 transition hover:border-red-400/50 hover:text-red-200"
          >
            <i className="ri-close-line text-[15px]" /> 반려하기
          </button>
        </div>
      )}

      {status === 'approved' && (
        <div className="mt-4 rounded-md border border-accent-500/30 bg-accent-500/10 p-3.5 text-[13px] text-accent-200">
          <p className="flex items-center gap-1.5">
            <i className="ri-checkbox-circle-fill" /> 승인 완료 · HEAD {review.candidateVersion}{' '}
            반영
          </p>
          <p className="mt-1 text-[11.5px] text-foreground-400">
            3줄 요약이 영향 팀 {review.teams.length}곳에 발송되었습니다.
          </p>
        </div>
      )}

      {status === 'rejected' && (
        <div className="mt-4 rounded-md border border-red-400/30 bg-red-400/10 p-3.5 text-[13px] text-red-200">
          <p className="flex items-center gap-1.5">
            <i className="ri-close-circle-fill" /> 반려되었습니다
          </p>
          <p className="mt-1 whitespace-pre-line text-[11.5px] text-foreground-400">{reason}</p>
        </div>
      )}

      {rejectOpen && status === 'pending' && (
        <div className="mt-4 rounded-md border border-background-700/70 bg-background-900/60 p-3.5">
          <label className="block">
            <span className="mb-1.5 block text-[12px] text-foreground-400">반려 사유</span>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={REJECT_REASON_MAX}
              rows={3}
              placeholder="어떤 부분을 보완해야 하는지 적어주세요."
              className="w-full resize-none rounded-md border border-background-600/70 bg-background-800/50 px-3 py-2 text-[13px] leading-relaxed text-foreground-100 outline-none transition placeholder:text-foreground-600 focus:border-primary-500/60"
            />
          </label>
          <div className="mt-2 flex items-center justify-between gap-2">
            <span className="font-label text-[11px] text-foreground-600">
              {reason.length} / {REJECT_REASON_MAX}
            </span>
            <button
              type="button"
              onClick={handleReject}
              disabled={reject.isPending}
              className="flex h-8 cursor-pointer items-center gap-1 whitespace-nowrap rounded-md bg-red-400/90 px-3 font-label text-[12.5px] font-semibold text-background-950 transition hover:bg-red-300"
            >
              <i className="ri-send-plane-line text-[13px]" /> 반려 제출
            </button>
          </div>
        </div>
      )}

      {confirmOpen && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-background-950/70 p-4 backdrop-blur-xs sm:items-center">
          <div
            role="dialog"
            aria-modal="true"
            className="w-full max-w-md rounded-lg border border-background-600/80 bg-background-900 p-5 shadow-panel"
          >
            <h3 className="font-heading text-[17px] text-foreground-50">
              승인하면 바로 알림이 발송됩니다
            </h3>
            <ul className="mt-3 space-y-2 text-[12.5px] leading-relaxed text-foreground-300">
              <li className="flex gap-2">
                <i className="ri-arrow-right-s-line text-primary-400" />
                {review.candidateVersion}이 HEAD가 되고 {review.headVersion}은 이력으로 보관됩니다.
              </li>
              <li className="flex gap-2">
                <i className="ri-arrow-right-s-line text-primary-400" />
                영향 팀 {review.teams.length}곳에 검증된 3줄 요약이 발송됩니다.
              </li>
              {showOverwrite && (
                <li className="flex gap-2">
                  <i className="ri-arrow-right-s-line text-primary-400" />
                  HEAD 덮어쓰기 {review.overwrite.count}곳은 반영 후 해결 여부가 기록됩니다.
                </li>
              )}
            </ul>
            <div className="mt-4 flex gap-2">
              <button
                type="button"
                onClick={() => approve.mutate()}
                disabled={approve.isPending}
                className="h-9 flex-1 cursor-pointer whitespace-nowrap rounded-md bg-primary-500 font-label text-[13px] font-semibold text-background-950 transition hover:bg-primary-400"
              >
                승인 확정
              </button>
              <button
                type="button"
                onClick={() => setConfirmOpen(false)}
                className="h-9 flex-1 cursor-pointer whitespace-nowrap rounded-md border border-background-600/80 font-label text-[13px] text-foreground-300 transition hover:bg-background-800/60"
              >
                취소
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}

export default ApprovalPanel
