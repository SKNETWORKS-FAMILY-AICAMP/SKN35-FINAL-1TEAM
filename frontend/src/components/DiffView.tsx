import type { ParagraphDiff } from '../api/documents'

export type DiffMode = 'split' | 'unified'

interface DiffViewProps {
  mode: DiffMode
  oldLabel: string
  newLabel: string
  paragraphs: ParagraphDiff[]
}

function AuthorTag({ author, version }: { author: string; version: string | null }) {
  return (
    <span className="mt-2 inline-flex items-center gap-1 rounded-full border border-background-600/70 bg-background-900/70 px-2 py-0.5 font-label text-[11px] text-foreground-400">
      <span className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-secondary-700/70 text-[8px] text-secondary-100">
        {author.slice(0, 1)}
      </span>
      {author} · {version}
    </span>
  )
}

function newRowClass(p: ParagraphDiff) {
  return `diff-row ${p.type === 'modified' ? 'diff-modified' : 'diff-added'}`
}

function Legend({ oldLabel, newLabel }: Pick<DiffViewProps, 'oldLabel' | 'newLabel'>) {
  return (
    <div className="sticky top-[68px] z-10 mb-3 flex flex-wrap items-center gap-2 rounded-md border border-background-700/70 bg-background-950/90 px-3 py-2 backdrop-blur-md">
      <span className="flex items-center gap-1.5 font-label text-[11.5px] uppercase tracking-[0.14em] text-foreground-500">
        <span className="h-1.5 w-1.5 rounded-full bg-foreground-500" />
        {oldLabel}
      </span>
      <i className="ri-arrow-right-line text-[11px] text-foreground-600" />
      <span className="flex items-center gap-1.5 font-label text-[11.5px] uppercase tracking-[0.14em] text-primary-300">
        <span className="h-1.5 w-1.5 rounded-full bg-primary-400" />
        {newLabel}
      </span>
      <span className="ml-auto flex flex-wrap items-center gap-2.5 font-label text-[11px] text-foreground-500">
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-sm bg-accent-500/70" /> 추가
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-sm bg-red-400/70" /> 삭제
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-sm bg-amber-400/70" /> 수정
        </span>
      </span>
    </div>
  )
}

function DiffView({ mode, oldLabel, newLabel, paragraphs }: DiffViewProps) {
  return (
    <div>
      <Legend oldLabel={oldLabel} newLabel={newLabel} />

      <div className={mode === 'split' ? 'space-y-2.5' : 'space-y-2'}>
        {paragraphs.map((p) => {
          const anchorId = `anchor-${p.id}`

          if (p.type === 'unchanged') {
            return (
              <div
                key={p.id}
                id={anchorId}
                className="scroll-mt-32 rounded-md px-3.5 py-2.5 text-[16.5px] leading-[1.8] text-foreground-300 md:px-4"
              >
                {p.after}
              </div>
            )
          }

          // 삭제된 문단은 after 가 비어 있고, 추가된 문단은 before 가 비어 있다
          const before = p.type === 'added' ? null : p.before
          const after = p.type === 'removed' ? null : p.after

          if (mode === 'unified') {
            return (
              <div key={p.id} id={anchorId} className="scroll-mt-32 space-y-1">
                {before && (
                  <div className="diff-row diff-removed">
                    <p className="diff-text text-[16px] leading-[1.75]">{before}</p>
                  </div>
                )}
                {after && (
                  <div className={newRowClass(p)}>
                    <p className="diff-text text-[16px] leading-[1.75]">{after}</p>
                    {p.author && <AuthorTag author={p.author} version={p.version} />}
                  </div>
                )}
              </div>
            )
          }

          return (
            <div
              key={p.id}
              id={anchorId}
              className="grid scroll-mt-32 grid-cols-1 gap-2 lg:grid-cols-2 lg:gap-3"
            >
              <div className={before ? 'diff-row diff-removed' : 'rounded-md px-4 py-3'}>
                {before ? (
                  <p className="text-[16px] leading-[1.75] text-red-200/90">{before}</p>
                ) : (
                  <p className="font-label text-[11.5px] uppercase tracking-[0.14em] text-foreground-700">
                    이전 버전에 없던 문단
                  </p>
                )}
              </div>
              <div className={after ? newRowClass(p) : 'rounded-md px-4 py-3'}>
                {after ? (
                  <>
                    <p className="text-[16px] leading-[1.75] text-foreground-50">{after}</p>
                    {p.author && <AuthorTag author={p.author} version={p.version} />}
                  </>
                ) : (
                  <p className="flex items-center gap-1.5 font-label text-[11.5px] uppercase tracking-[0.14em] text-red-300/80">
                    <i className="ri-delete-bin-6-line text-[12px]" /> 이 문단이 삭제되었습니다
                  </p>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default DiffView
