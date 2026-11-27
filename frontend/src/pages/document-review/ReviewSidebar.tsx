import type { ChangeItem, DocumentReview } from '../../api/documents'
import Badge from '../../components/Badge'
import type { ApprovalStatus } from './ApprovalPanel'

const CHANGE_TYPES: ChangeItem['type'][] = ['추가', '삭제', '수정']

const CHANGE_STYLE: Record<ChangeItem['type'], { bar: string; text: string }> = {
  추가: { bar: 'bg-accent-500', text: 'text-accent-400' },
  삭제: { bar: 'bg-red-400', text: 'text-red-300' },
  수정: { bar: 'bg-amber-400', text: 'text-amber-300' },
}

const APPROVAL_STATUS = {
  pending: {
    icon: 'ri-time-line',
    color: 'text-foreground-300',
    label: '승인 대기 중',
    desc: '이 문서는 승인권자만 처리할 수 있습니다.',
  },
  approved: {
    icon: 'ri-checkbox-circle-fill',
    color: 'text-accent-300',
    label: '승인 완료 · HEAD 반영',
    desc: '3줄 요약이 확정된 팀에 발송되었습니다.',
  },
  rejected: {
    icon: 'ri-close-circle-fill',
    color: 'text-red-300',
    label: '반려됨',
    desc: '반려 사유는 작성자와 같은 팀에만 공개됩니다.',
  },
} satisfies Record<ApprovalStatus, { icon: string; color: string; label: string; desc: string }>

function scrollToParagraph(paragraphId: string) {
  document
    .getElementById(`anchor-${paragraphId}`)
    ?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

interface ReviewSidebarProps {
  review: DocumentReview
  approvalStatus: ApprovalStatus
  onResetApproval: () => void
}

function ReviewSidebar({ review, approvalStatus, onResetApproval }: ReviewSidebarProps) {
  const counts = Object.fromEntries(
    CHANGE_TYPES.map((type) => [type, review.changeItems.filter((c) => c.type === type).length]),
  ) as Record<ChangeItem['type'], number>
  const doneCount = review.teams.filter((t) => t.state === 'done').length
  const status = APPROVAL_STATUS[approvalStatus]

  return (
    <aside className="space-y-3 xl:sticky xl:top-[96px] xl:self-start">
      <div className="panel p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-heading text-[15px] font-medium text-foreground-50">변경 요약</h2>
          <span className="font-label text-[11px] uppercase tracking-[0.14em] text-foreground-600">
            총 {review.changeItems.length}건
          </span>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2">
          {CHANGE_TYPES.map((type) => (
            <div
              key={type}
              className="rounded-md border border-background-700/70 bg-background-800/40 px-2 py-2 text-center"
            >
              <p className={`stat-value text-[19px] leading-none ${CHANGE_STYLE[type].text}`}>
                {counts[type]}
              </p>
              <p className="mt-1 text-[11.5px] text-foreground-500">{type}</p>
            </div>
          ))}
        </div>
        <ul className="mt-3 space-y-1">
          {review.changeItems.map((item) => (
            <li key={item.paragraphId}>
              <button
                type="button"
                onClick={() => scrollToParagraph(item.paragraphId)}
                className="flex w-full cursor-pointer items-start gap-2 rounded-sm px-1.5 py-1.5 text-left transition hover:bg-background-800/60"
              >
                <span
                  className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${CHANGE_STYLE[item.type].bar}`}
                />
                <span className="min-w-0 flex-1 text-[12.5px] leading-relaxed text-foreground-300">
                  {item.label}
                </span>
                <i className="ri-arrow-down-s-line mt-0.5 text-[13px] text-foreground-600" />
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="panel p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-heading text-[15px] font-medium text-foreground-50">3줄 요약</h2>
          {review.verification.passed && (
            <Badge tone="accent" icon="ri-checkbox-circle-line">
              검증 통과
            </Badge>
          )}
        </div>
        <ol className="mt-3 space-y-2">
          {review.summary.map((line, i) => (
            <li key={line} className="flex gap-2 text-[12.5px] leading-relaxed text-foreground-300">
              <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-background-700/80 font-label text-[9px] text-foreground-400">
                {i + 1}
              </span>
              {line}
            </li>
          ))}
        </ol>
        <p className="mt-3 flex items-center gap-1 border-t border-background-700/60 pt-2.5 text-[11px] text-foreground-600">
          <i className="ri-robot-2-line text-[13px] text-primary-400" />
          {review.verification.agent} · 재작성 {review.verification.rewrites}회 ·{' '}
          {review.verification.checkedAt}
        </p>
      </div>

      <div className="panel p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-heading text-[15px] font-medium text-foreground-50">영향 팀 확인</h2>
          <span className="font-label text-[11.5px] text-foreground-500">
            {doneCount}/{review.teams.length} 확인
          </span>
        </div>
        <ul className="mt-3 space-y-2">
          {review.teams.map((team) => (
            <li
              key={team.name}
              className="flex items-center justify-between gap-2 rounded-md border border-background-700/70 bg-background-800/30 px-2.5 py-2"
            >
              <span className="flex items-center gap-1.5 text-[13px] text-foreground-100">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${team.state === 'done' ? 'bg-accent-400' : 'bg-amber-400'}`}
                />
                {team.name}
              </span>
              {team.state === 'done' ? (
                <span className="flex items-center gap-1 text-[11.5px] text-accent-400">
                  <i className="ri-check-line" /> 확인 완료
                  {team.response && team.response !== '확인 완료' && (
                    <span className="text-foreground-500">· {team.response}</span>
                  )}
                </span>
              ) : (
                <span className="text-[11.5px] text-amber-300">미확인</span>
              )}
            </li>
          ))}
        </ul>
        <p className="mt-2.5 text-[11px] leading-relaxed text-foreground-600">
          확인 응답은 담당자만 남길 수 있습니다. 이 영역은 현황만 표시합니다.
        </p>
      </div>

      <div className="panel p-4">
        <h2 className="font-heading text-[15px] font-medium text-foreground-50">승인 상태</h2>
        <p className={`mt-2 flex items-center gap-1.5 text-[13px] ${status.color}`}>
          <i className={status.icon} />
          {status.label}
        </p>
        <p className="mt-1.5 text-[11.5px] leading-relaxed text-foreground-500">{status.desc}</p>
        {approvalStatus !== 'pending' && (
          <button
            type="button"
            onClick={onResetApproval}
            className="mt-2 cursor-pointer text-[11.5px] text-foreground-400 underline-offset-2 hover:text-foreground-100 hover:underline"
          >
            되돌리기
          </button>
        )}
      </div>
    </aside>
  )
}

export default ReviewSidebar
