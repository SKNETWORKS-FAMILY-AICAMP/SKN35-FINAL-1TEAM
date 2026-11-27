import { useState } from 'react'

import type { ParagraphDiff } from '../../api/documents'
import type { AnalysisResult, ApprovalRequestBody, ImpactCandidate } from '../../api/submissions'
import Badge from '../../components/Badge'

type SummaryScenario = 'verified' | 'failed'

const SCENARIOS: { key: SummaryScenario; label: string }[] = [
  { key: 'verified', label: '요약 검증 통과' },
  { key: 'failed', label: '요약 검증 실패' },
]

const CONFIDENCE_CLASS: Record<ImpactCandidate['confidence'], string> = {
  높음: 'text-accent-300',
  보통: 'text-amber-300',
  낮음: 'bg-background-700/70 text-foreground-400',
}

const SUMMARY_MAX = 500

function diffRowClass(type: ParagraphDiff['type']) {
  if (type === 'added') return 'diff-row diff-added'
  if (type === 'removed') return 'diff-row diff-removed'
  return 'diff-row diff-modified'
}

function ChangedParagraphs({
  paragraphs,
  compact,
}: {
  paragraphs: ParagraphDiff[]
  compact?: boolean
}) {
  const oldText = compact ? 'text-[12px]' : 'text-[13px]'
  const newText = compact ? 'text-[12.5px]' : 'text-[14px]'

  return (
    <div className="mt-3 space-y-2">
      {paragraphs.map((p) => (
        <div key={p.id} className={diffRowClass(p.type)}>
          {p.type !== 'added' && (
            <p className={`${oldText} leading-relaxed text-red-200/80 line-through`}>{p.before}</p>
          )}
          {p.type !== 'removed' && (
            <p
              className={`${p.type === 'modified' ? 'mt-1' : ''} ${newText} leading-relaxed text-foreground-50`}
            >
              {p.after}
            </p>
          )}
        </div>
      ))}
    </div>
  )
}

interface ReviewStepProps {
  result: AnalysisResult
  submitting: boolean
  onBack: () => void
  onRequestApproval: (body: ApprovalRequestBody) => void
}

function ReviewStep({ result, submitting, onBack, onRequestApproval }: ReviewStepProps) {
  const [teams, setTeams] = useState(result.impactTeams)
  const [addOpen, setAddOpen] = useState(false)
  const [excludeReason, setExcludeReason] = useState('')
  const [scenario, setScenario] = useState<SummaryScenario>('verified')
  const [summaryOverride, setSummaryOverride] = useState('')

  const included = teams.filter((t) => t.checked)
  const excluded = teams.filter((t) => !t.checked)
  const addedCount = result.paragraphs.filter((p) => p.type === 'added').length
  const modifiedCount = result.paragraphs.filter((p) => p.type === 'modified').length

  const setChecked = (name: string, checked: boolean) =>
    setTeams((prev) => prev.map((t) => (t.name === name ? { ...t, checked } : t)))

  return (
    <div className="space-y-4">
      <section className="panel flex flex-wrap items-center gap-3 p-3">
        <span className="flex items-center gap-1.5 font-label text-[11px] uppercase tracking-[0.16em] text-foreground-600">
          <i className="ri-flask-line text-[13px]" /> 결과 시나리오 (데모)
        </span>
        <div className="flex h-8 items-center rounded-full border border-background-600/70 bg-background-900/60 p-1">
          {SCENARIOS.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => setScenario(item.key)}
              className={`h-6 cursor-pointer whitespace-nowrap rounded-full px-3 font-label text-[12px] transition ${scenario === item.key ? 'bg-foreground-50 text-background-950' : 'text-foreground-400 hover:text-foreground-100'}`}
            >
              {item.label}
            </button>
          ))}
        </div>
        <span className="ml-auto text-[11.5px] text-foreground-600">
          {scenario === 'verified'
            ? 'AI 3줄 요약이 표시됩니다.'
            : '검증 실패 시 원문이 그대로 표시됩니다.'}
        </span>
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
        <section className="space-y-3">
          <div className="panel p-4 md:p-5">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-heading text-[15px] text-foreground-50">변경 내용 확인</h2>
              <div className="flex items-center gap-1.5">
                <Badge tone="accent">추가 {addedCount}</Badge>
                <Badge tone="warning">수정 {modifiedCount}</Badge>
              </div>
            </div>
            <ChangedParagraphs paragraphs={result.paragraphs} />
          </div>

          <div className="panel p-4 md:p-5">
            <h2 className="font-heading text-[15px] text-foreground-50">영향 팀 확인</h2>
            <p className="mt-1 text-[12px] leading-relaxed text-foreground-500">
              AI가 영향 있다고 판정한 팀은 이미 알림 대상에 포함되어 있습니다. 불필요한 팀만
              제외하세요.
            </p>
            <ul className="mt-3 space-y-2">
              {teams.map((team) => (
                <li
                  key={team.name}
                  className={`rounded-md border p-3 transition ${team.checked ? 'border-primary-500/30 bg-primary-500/[0.05]' : 'border-background-700/70 bg-background-800/20 opacity-85'}`}
                >
                  <div className="flex items-start gap-2.5">
                    <button
                      type="button"
                      onClick={() => setChecked(team.name, !team.checked)}
                      aria-label={`${team.name} 알림 대상 ${team.checked ? '제외' : '포함'}`}
                      className={`mt-0.5 flex h-4 w-4 shrink-0 cursor-pointer items-center justify-center rounded-sm border transition ${team.checked ? 'border-primary-400 bg-primary-400 text-background-950' : 'border-background-500 text-transparent'}`}
                    >
                      <i className="ri-check-line text-[12px]" />
                    </button>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-[14px] text-foreground-100">{team.name}</span>
                        <span
                          className={`rounded-sm px-1.5 py-0.5 font-label text-[10.5px] uppercase tracking-wider ${CONFIDENCE_CLASS[team.confidence]}`}
                        >
                          확신도 {team.confidence}
                        </span>
                        {!team.checked && (
                          <span className="text-[10.5px] text-foreground-600">알림 제외</span>
                        )}
                      </div>
                      <p className="mt-1 text-[12px] leading-relaxed text-foreground-500">
                        {team.reason}
                      </p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setAddOpen((open) => !open)}
                  className="flex h-8 cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-md border border-background-600/80 px-2.5 text-[12px] text-foreground-300 transition hover:border-primary-500/40 hover:text-primary-200"
                >
                  <i className="ri-add-line text-[13px]" /> 팀 추가
                </button>
                {addOpen && (
                  <div className="absolute left-0 top-9 z-20 w-[220px] rounded-md border border-background-600/80 bg-background-900 p-1 shadow-panel">
                    {excluded.length === 0 ? (
                      <p className="px-2.5 py-2 text-[12px] text-foreground-500">
                        모든 팀이 이미 포함되어 있습니다.
                      </p>
                    ) : (
                      excluded.map((team) => (
                        <button
                          key={team.name}
                          type="button"
                          onClick={() => {
                            setChecked(team.name, true)
                            setAddOpen(false)
                          }}
                          className="flex w-full cursor-pointer items-center justify-between rounded-sm px-2.5 py-2 text-[12.5px] text-foreground-300 transition hover:bg-background-700/70 hover:text-foreground-50"
                        >
                          {team.name}
                          <i className="ri-add-line text-[13px]" />
                        </button>
                      ))
                    )}
                  </div>
                )}
              </div>
              <input
                value={excludeReason}
                onChange={(e) => setExcludeReason(e.target.value)}
                placeholder="제외 사유 (선택 · 판정 개선에 사용)"
                className="h-8 min-w-[180px] flex-1 rounded-md border border-background-600/70 bg-background-800/50 px-2.5 text-[12px] text-foreground-100 outline-none focus:border-primary-500/60"
              />
              <span className="ml-auto font-label text-[11.5px] text-foreground-500">
                알림 대상 {included.length}팀
              </span>
            </div>
          </div>
        </section>

        <aside className="space-y-3">
          {scenario === 'verified' ? (
            <div className="panel p-4">
              <div className="flex items-center justify-between">
                <h2 className="font-heading text-[15.5px] text-foreground-50">AI 3줄 요약</h2>
                <Badge tone="accent" icon="ri-checkbox-circle-line">
                  검증 통과
                </Badge>
              </div>
              <ol className="mt-3 space-y-2">
                {result.summary.map((line, i) => (
                  <li
                    key={line}
                    className="flex gap-2 text-[12.5px] leading-relaxed text-foreground-300"
                  >
                    <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-background-700/80 font-label text-[9px] text-foreground-400">
                      {i + 1}
                    </span>
                    {line}
                  </li>
                ))}
              </ol>
              <p className="mt-3 border-t border-background-700/60 pt-2.5 text-[11px] text-foreground-600">
                요약 에이전트 → 검증 에이전트 1회 재작성 후 통과. 승인 시 이 문구가 그대로 알림에
                사용됩니다.
              </p>
            </div>
          ) : (
            <div className="panel border-amber-400/25 p-4">
              <div className="flex items-center justify-between">
                <h2 className="font-heading text-[15.5px] text-foreground-50">3줄 요약</h2>
                <Badge tone="warning" icon="ri-error-warning-line">
                  검증 실패
                </Badge>
              </div>
              <p className="mt-3 rounded-md border border-amber-400/25 bg-amber-400/[0.07] px-3 py-2.5 text-[12.5px] leading-relaxed text-amber-100">
                AI 요약 생략: 원문 대조 검증을 통과하지 못해 바뀐 문단을 그대로 보여드립니다
              </p>
              <ChangedParagraphs paragraphs={result.paragraphs} compact />
              <label className="mt-3 block">
                <span className="mb-1 block text-[11.5px] text-foreground-500">요약 직접 작성</span>
                <textarea
                  value={summaryOverride}
                  onChange={(e) => setSummaryOverride(e.target.value)}
                  maxLength={SUMMARY_MAX}
                  rows={3}
                  placeholder="요약을 직접 작성할 수 있어요 (선택)"
                  className="w-full resize-none rounded-md border border-background-600/70 bg-background-800/50 px-3 py-2 text-[12.5px] leading-relaxed text-foreground-100 outline-none transition placeholder:text-foreground-600 focus:border-primary-500/60"
                />
              </label>
              <p className="mt-1 text-right font-label text-[10.5px] text-foreground-600">
                {summaryOverride.length} / {SUMMARY_MAX}
              </p>
            </div>
          )}

          <div className="panel p-4">
            {scenario === 'failed' && (
              <p className="mb-2 flex items-start gap-1.5 rounded-md border border-background-700/70 bg-background-800/40 px-2.5 py-2 text-[11px] leading-relaxed text-foreground-500">
                <i className="ri-information-line mt-px text-[13px] text-primary-400" />
                요약을 직접 작성하지 않으면 바뀐 문단 원문이 그대로 알림에 전달됩니다.
              </p>
            )}
            <button
              type="button"
              disabled={submitting}
              onClick={() =>
                onRequestApproval({
                  teams: included.map((t) => t.name),
                  excludeReason,
                  summaryOverride,
                })
              }
              className="h-9 w-full cursor-pointer whitespace-nowrap rounded-md bg-primary-500 font-label text-[13px] font-semibold text-background-950 shadow-glow transition hover:bg-primary-400"
            >
              승인 요청 보내기
            </button>
            <p className="mt-2 text-[11px] leading-relaxed text-foreground-600">
              승인자: {result.approvers}. 본인 문서는 본인이 승인할 수 없습니다.
            </p>
            <button
              type="button"
              onClick={onBack}
              className="mt-2 w-full cursor-pointer text-[11.5px] text-foreground-500 transition hover:text-foreground-100"
            >
              이전 단계로
            </button>
          </div>
        </aside>
      </div>
    </div>
  )
}

export default ReviewStep
