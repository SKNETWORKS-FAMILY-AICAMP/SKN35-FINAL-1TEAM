import type { SubmissionAnalysis } from '../../api/submissions'

const STEP_STYLE = {
  done: {
    row: 'border-background-700/70 bg-background-800/30',
    icon: 'bg-accent-500/15 text-accent-400',
  },
  active: {
    row: 'border-primary-500/40 bg-primary-500/[0.06] shadow-glow',
    icon: 'bg-primary-500/20 text-primary-300',
  },
  idle: {
    row: 'border-background-800/80',
    icon: 'bg-background-700/60 text-foreground-600',
  },
}

interface AnalyzingStepProps {
  fileName: string
  compareLabel: string
  analysis: SubmissionAnalysis | undefined
  onRetry: () => void
}

function AnalyzingStep({ fileName, compareLabel, analysis, onRetry }: AnalyzingStepProps) {
  const steps = analysis?.steps ?? []
  const completed = analysis?.completedSteps ?? 0
  const failed = analysis?.status === 'failed'

  return (
    <section className="panel mx-auto max-w-2xl p-6 md:p-8">
      <div className="flex items-center gap-3">
        <span className="flex h-10 w-10 items-center justify-center rounded-full border border-primary-500/40 bg-primary-500/10 text-primary-300">
          <i
            className={
              failed ? 'ri-error-warning-line text-lg' : 'ri-loader-4-line animate-spin text-lg'
            }
          />
        </span>
        <div>
          <h2 className="font-heading text-[17px] text-foreground-50">
            {failed ? '분석에 실패했어요' : '변경 내용을 분석하고 있어요'}
          </h2>
          <p className="mt-0.5 text-[12.5px] text-foreground-500">
            {fileName} · {compareLabel} · 보통 20~40초 소요
          </p>
        </div>
      </div>

      <div className="mt-6 space-y-3">
        {steps.map((step, i) => {
          const state = i < completed ? 'done' : i === completed ? 'active' : 'idle'
          return (
            <div
              key={step.label}
              className={`flex items-start gap-3 rounded-md border px-3.5 py-3 transition ${STEP_STYLE[state].row}`}
            >
              <span
                className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${STEP_STYLE[state].icon}`}
              >
                {state === 'done' ? (
                  <i className="ri-check-line text-[13px]" />
                ) : state === 'active' ? (
                  <i className="ri-loader-4-line animate-spin text-[13px]" />
                ) : (
                  <span className="h-1.5 w-1.5 rounded-full bg-current" />
                )}
              </span>
              <div className="min-w-0 flex-1">
                <p
                  className={`text-[14px] ${state === 'idle' ? 'text-foreground-500' : 'text-foreground-100'}`}
                >
                  {step.label}
                </p>
                <p className="mt-0.5 text-[11.5px] text-foreground-500">{step.detail}</p>
              </div>
              {state === 'done' && (
                <span className="font-label text-[11px] text-accent-400">완료</span>
              )}
            </div>
          )
        })}
      </div>

      <div className="mt-5 h-1 overflow-hidden rounded-full bg-background-700">
        <div
          className="h-full rounded-full bg-primary-500 transition-all duration-700"
          style={{ width: `${steps.length ? (completed / steps.length) * 100 : 0}%` }}
        />
      </div>

      {failed && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-5 flex h-9 cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-md border border-background-600/80 px-4 text-[13px] text-foreground-200 transition hover:bg-background-800/60"
        >
          <i className="ri-arrow-left-line text-[13px]" /> 다시 제출하기
        </button>
      )}
    </section>
  )
}

export default AnalyzingStep
