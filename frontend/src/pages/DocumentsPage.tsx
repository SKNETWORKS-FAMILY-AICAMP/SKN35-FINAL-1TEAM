import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link } from 'react-router'

import { documentQueries, type FileExt, type Scope } from '../api/documents'
import Badge, { type BadgeTone } from '../components/Badge'
import { useCurrentUser } from '../hooks/useAuth'

const ALL_TEAMS = '전체'

const SCOPE_TONE: Record<Scope, BadgeTone> = {
  '사내 공개': 'primary',
  '프로젝트 내부': 'neutral',
  '팀 내부': 'warning',
  '외부 공유': 'accent',
}

const SCOPE_POLICIES: { scope: Scope; desc: string }[] = [
  { scope: '사내 공개', desc: '프로젝트 밖 사내 구성원도 열람·검색' },
  { scope: '프로젝트 내부', desc: '프로젝트 멤버와 소유 팀 (기본값)' },
  { scope: '팀 내부', desc: '소유 팀만 열람 · 영향 알림도 팀 내부' },
  { scope: '외부 공유', desc: '초대된 게스트까지 열람·검색' },
]

const EXT_ICON: Partial<Record<FileExt, string>> = {
  PPTX: 'ri-slideshow-line',
  XLSX: 'ri-table-line',
  DOCX: 'ri-file-word-2-line',
}

function DocumentsPage() {
  const { project, teams } = useCurrentUser()
  const [team, setTeam] = useState(ALL_TEAMS)
  const [keyword, setKeyword] = useState('')
  const [pendingOnly, setPendingOnly] = useState(false)

  const { data: documents = [] } = useQuery(documentQueries.list())

  // 팀 필터는 프로젝트 팀 목록 API 기준
  const teamFilters = [ALL_TEAMS, ...teams.flatMap((t) => (t.name ? [t.name] : []))]

  const filtered = useMemo(() => {
    const q = keyword.trim()
    return documents.filter(
      (doc) =>
        (team === ALL_TEAMS || doc.team === team) &&
        (!q || doc.name.includes(q) || doc.summary.includes(q)) &&
        (!pendingOnly || doc.pending),
    )
  }, [documents, team, keyword, pendingOnly])

  const resetFilters = () => {
    setTeam(ALL_TEAMS)
    setKeyword('')
    setPendingOnly(false)
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="overline">{project.name} · 문서</p>
          <h1 className="mt-3 font-heading text-[28px] leading-tight text-foreground-50 md:text-[34px]">
            <span className="font-semibold">기준</span>{' '}
            <span className="font-light text-foreground-200">문서</span>
          </h1>
          <p className="mt-2 max-w-xl text-[14px] leading-relaxed text-foreground-400">
            승인된 HEAD 버전과 공개 범위를 확인합니다. 버전은 문서마다 따로 매겨지고, 승인 대기 중인
            제출본은 ‘검토 중’으로 표시됩니다.
          </p>
        </div>
        <Link
          to="/submit"
          className="flex h-9 w-fit cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-md bg-foreground-50 px-4 text-[13.5px] font-medium text-background-950 transition hover:bg-foreground-100"
        >
          <i className="ri-upload-cloud-2-line text-[16px]" /> 변경 제출
        </Link>
      </section>

      <section className="flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap items-center gap-1 rounded-full border border-background-700/70 bg-background-900/60 p-1">
          {teamFilters.map((name) => (
            <button
              key={name}
              type="button"
              onClick={() => setTeam(name)}
              className={`h-7 cursor-pointer whitespace-nowrap rounded-full px-3 font-label text-[12.5px] transition ${team === name ? 'bg-foreground-50 text-background-950' : 'text-foreground-400 hover:text-foreground-100'}`}
            >
              {name}
            </button>
          ))}
        </div>
        <div className="relative min-w-[200px] flex-1 md:max-w-[280px]">
          <span className="pointer-events-none absolute left-3 top-1/2 flex h-4 w-4 -translate-y-1/2 items-center justify-center text-foreground-500">
            <i className="ri-search-line text-[14px]" />
          </span>
          <input
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="문서명 또는 요약 검색"
            className="h-9 w-full rounded-md border border-background-600/70 bg-background-800/50 pl-9 pr-3 text-[13.5px] text-foreground-100 outline-none transition placeholder:text-foreground-600 focus:border-primary-500/60"
          />
        </div>
        <button
          type="button"
          onClick={() => setPendingOnly((v) => !v)}
          aria-pressed={pendingOnly}
          className={`flex h-9 cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-md border px-3 text-[12.5px] transition ${pendingOnly ? 'border-primary-500/50 bg-primary-500/10 text-primary-200' : 'border-background-600/70 text-foreground-400 hover:text-foreground-100'}`}
        >
          <i className={`text-[14px] ${pendingOnly ? 'ri-filter-3-fill' : 'ri-filter-3-line'}`} />
          승인 대기만
        </button>
        <span className="ml-auto font-label text-[12px] text-foreground-500">
          {filtered.length} / {documents.length} 건
        </span>
      </section>

      <section className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((doc) => (
          <Link
            key={doc.id}
            to={`/documents/${doc.id}`}
            className="panel group flex cursor-pointer flex-col p-4 transition hover:border-primary-500/35 hover:bg-background-800/50"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-sm border border-background-600/70 bg-background-800/70 text-[14px] text-foreground-400">
                  <i className={EXT_ICON[doc.ext] ?? 'ri-markdown-line'} />
                </span>
                <div className="min-w-0">
                  <p className="flex items-center gap-1.5 truncate text-[14px] text-foreground-50 transition group-hover:text-primary-200">
                    {doc.name}
                    {doc.pending && <span className="h-1.5 w-1.5 rounded-full bg-red-400" />}
                  </p>
                  <p className="text-[11.5px] text-foreground-600">
                    {doc.team} · {doc.owner}
                  </p>
                </div>
              </div>
              <span className="shrink-0 rounded-sm border border-background-600/70 px-1.5 py-0.5 font-label text-[11px] text-foreground-400">
                {doc.ext}
              </span>
            </div>
            <p className="mt-3 line-clamp-2 text-[13px] leading-relaxed text-foreground-400">
              {doc.summary}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              <Badge tone="primary">HEAD v{doc.version}</Badge>
              <Badge tone={SCOPE_TONE[doc.scope]}>{doc.scope}</Badge>
              {doc.pending && (
                <Badge tone="warning" dot>
                  v{doc.version + 1} 검토 중
                </Badge>
              )}
            </div>
            <div className="mt-auto flex items-center justify-between border-t border-background-700/60 pt-2.5 text-[11.5px] text-foreground-600">
              <span>
                {doc.updatedAt} 반영 · {doc.size}
              </span>
              <span className="flex items-center gap-1 text-foreground-500 transition group-hover:text-primary-300">
                변경 {doc.changes}건 <i className="ri-arrow-right-up-line text-[13px]" />
              </span>
            </div>
          </Link>
        ))}
      </section>

      {filtered.length === 0 && (
        <div className="panel flex flex-col items-center justify-center gap-2 py-16 text-center">
          <span className="flex h-10 w-10 items-center justify-center rounded-full border border-background-600/70 text-foreground-500">
            <i className="ri-file-search-line text-lg" />
          </span>
          <p className="text-[14px] text-foreground-300">조건에 맞는 문서가 없습니다.</p>
          <button
            type="button"
            onClick={resetFilters}
            className="mt-1 cursor-pointer text-[12.5px] text-primary-300 hover:text-primary-200"
          >
            필터 초기화
          </button>
        </div>
      )}

      <section className="panel p-5">
        <h2 className="font-heading text-[16px] font-medium text-foreground-50">공개 범위 정책</h2>
        <ul className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          {SCOPE_POLICIES.map((policy) => (
            <li key={policy.scope} className="flex items-start gap-2.5">
              <Badge tone={SCOPE_TONE[policy.scope]} className="shrink-0">
                {policy.scope}
              </Badge>
              <span className="text-[12.5px] leading-relaxed text-foreground-400">
                {policy.desc}
              </span>
            </li>
          ))}
        </ul>
        <p className="mt-4 flex items-start gap-1.5 rounded-md border border-background-600/60 bg-background-800/40 p-2.5 text-[11.5px] leading-relaxed text-foreground-500">
          <i className="ri-shield-check-line mt-px text-[14px] text-primary-400" />
          권한 판정은 모델이 아니라 DB 규칙으로 처리되고, 검색 단계에서 필터가 적용됩니다.
        </p>
      </section>
    </div>
  )
}

export default DocumentsPage
