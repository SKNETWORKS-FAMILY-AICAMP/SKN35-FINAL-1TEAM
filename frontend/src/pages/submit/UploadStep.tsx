import { useQuery } from '@tanstack/react-query'
import { useState, type DragEvent } from 'react'
import { Link } from 'react-router'

import { documentQueries, type DocumentSummary } from '../../api/documents'
import type { SubmissionMode } from '../../api/submissions'
import Badge from '../../components/Badge'

const ACCEPTED_EXTENSIONS = ['pdf', 'docx', 'pptx', 'hwpx', 'xlsx', 'md', 'txt']
const PROJECT_DOC_PREVIEW = 4

const EXT_ICON: Record<string, string> = {
  docx: 'ri-file-word-2-line',
  pptx: 'ri-slideshow-line',
  xlsx: 'ri-table-line',
  pdf: 'ri-file-pdf-2-line',
  md: 'ri-markdown-line',
}

const CHECKLIST = [
  '같은 문서에 승인 요청이 있으면 새로 제출할 수 없습니다.',
  'AI가 영향 있다고 본 팀은 기본으로 알림 대상에 들어갑니다.',
  '변경된 기준의 적용 시점을 함께 적어두세요.',
]

function getExtension(name: string) {
  return name.split('.').pop()?.toLowerCase() ?? ''
}

function formatSize(bytes: number) {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

interface UploadStepProps {
  file: File | null
  mode: SubmissionMode
  teamDocuments: DocumentSummary[]
  selectedDoc: DocumentSummary | undefined
  submitting: boolean
  error: string
  onFileChange: (file: File | null) => void
  onModeChange: (mode: SubmissionMode) => void
  onDocumentChange: (documentId: string) => void
  onStart: () => void
}

function ModeOption({
  selected,
  disabled = false,
  title,
  desc,
  onClick,
}: {
  selected: boolean
  disabled?: boolean
  title: string
  desc: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`cursor-pointer rounded-md border px-3.5 py-3 text-left transition disabled:cursor-not-allowed disabled:opacity-40 ${selected ? 'border-primary-500/50' : 'border-background-600/70 hover:border-background-500'}`}
    >
      <span className="flex items-center justify-between">
        <span className="text-[14px] text-foreground-100">{title}</span>
        <span
          className={`h-3.5 w-3.5 rounded-full border ${selected ? 'border-primary-400 bg-primary-400' : 'border-background-500'}`}
        />
      </span>
      <span className="mt-1 block text-[11.5px] text-foreground-500">{desc}</span>
    </button>
  )
}

function UploadStep({
  file,
  mode,
  teamDocuments,
  selectedDoc,
  submitting,
  error,
  onFileChange,
  onModeChange,
  onDocumentChange,
  onStart,
}: UploadStepProps) {
  const [dragging, setDragging] = useState(false)
  const [fileError, setFileError] = useState('')
  const { data: documents = [] } = useQuery(documentQueries.list())

  const selectFile = (next: File | undefined) => {
    if (!next) return
    if (!ACCEPTED_EXTENSIONS.includes(getExtension(next.name))) {
      setFileError('지원하지 않는 형식입니다. 텍스트를 추출할 수 있는 파일만 올릴 수 있습니다.')
      return
    }
    setFileError('')
    onFileChange(next)
  }

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragging(false)
    selectFile(e.dataTransfer.files?.[0])
  }

  const ext = file ? getExtension(file.name) : ''

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_330px]">
      <section className="panel p-4 md:p-5">
        <div
          onDragOver={(e) => {
            e.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={`flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed px-6 py-12 text-center transition ${dragging ? 'border-primary-500' : 'border-background-500/80 bg-background-900/40 hover:border-primary-500/50'}`}
        >
          <span className="flex h-12 w-12 items-center justify-center rounded-full border border-background-600 bg-background-800/70 text-primary-300">
            <i className="ri-upload-cloud-2-line text-xl" />
          </span>
          <div>
            <p className="text-[15.5px] text-foreground-100">파일을 끌어다 놓거나 선택하세요</p>
            <p className="mt-1 text-[12.5px] text-foreground-500">
              {ACCEPTED_EXTENSIONS.map((e) => e.toUpperCase()).join(' · ')} (텍스트 추출 가능한
              파일)
            </p>
          </div>
          <label className="mt-1 flex h-8 cursor-pointer items-center gap-1.5 rounded-md border border-background-600/80 px-3 text-[12.5px] text-foreground-200 transition hover:border-primary-500/50 hover:text-primary-200">
            <i className="ri-folder-open-line text-[13px]" /> 파일 선택
            <input
              type="file"
              accept={ACCEPTED_EXTENSIONS.map((e) => `.${e}`).join(',')}
              className="hidden"
              onChange={(e) => {
                selectFile(e.target.files?.[0])
                e.target.value = ''
              }}
            />
          </label>
        </div>

        {fileError && (
          <p className="mt-3 flex items-center gap-1.5 text-[12px] text-red-300">
            <i className="ri-error-warning-line text-[13px]" /> {fileError}
          </p>
        )}

        {file && (
          <div className="mt-4 rounded-md border border-background-700/70 bg-background-800/40 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-sm border border-background-600/70 text-[15.5px] text-foreground-400">
                <i className={EXT_ICON[ext] ?? 'ri-file-text-line'} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-[14px] text-foreground-100">{file.name}</p>
                <p className="text-[11.5px] text-foreground-500">
                  {ext.toUpperCase()} · {formatSize(file.size)} · 업로드 준비됨
                </p>
              </div>
              <Badge tone="accent" icon="ri-check-line">
                형식 확인
              </Badge>
              <button
                type="button"
                onClick={() => onFileChange(null)}
                aria-label="파일 제거"
                className="flex h-7 w-7 cursor-pointer items-center justify-center rounded-sm text-foreground-500 transition hover:bg-background-700/70 hover:text-foreground-100"
              >
                <i className="ri-close-line text-[15.5px]" />
              </button>
            </div>
          </div>
        )}

        <div className="mt-5">
          <p className="font-label text-[11px] uppercase tracking-[0.18em] text-foreground-600">
            문서 연결
          </p>
          <div className="mt-2.5 grid grid-cols-1 gap-2 sm:grid-cols-2">
            <ModeOption
              selected={mode === 'existing'}
              disabled={teamDocuments.length === 0}
              title="기존 문서의 새 버전"
              desc={
                selectedDoc
                  ? `${selectedDoc.name} · HEAD v${selectedDoc.version} → v${selectedDoc.version + 1}`
                  : '우리 팀 문서가 아직 없습니다'
              }
              onClick={() => onModeChange('existing')}
            />
            <ModeOption
              selected={mode === 'new'}
              title="새 문서로 등록"
              desc="문서명은 파일명으로 자동 입력"
              onClick={() => onModeChange('new')}
            />
          </div>

          {mode === 'existing' && selectedDoc ? (
            <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
              <label className="block">
                <span className="mb-1 block text-[11.5px] text-foreground-500">우리 팀 문서</span>
                <select
                  value={selectedDoc.id}
                  onChange={(e) => onDocumentChange(e.target.value)}
                  className="h-9 w-full cursor-pointer rounded-md border border-background-600/70 bg-background-800/50 px-2.5 text-[13px] text-foreground-100 outline-none focus:border-primary-500/60"
                >
                  {teamDocuments.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block">
                <span className="mb-1 block text-[11.5px] text-foreground-500">기준 버전 선택</span>
                <select className="h-9 w-full cursor-pointer rounded-md border border-background-600/70 bg-background-800/50 px-2.5 text-[13px] text-foreground-100 outline-none focus:border-primary-500/60">
                  <option>HEAD v{selectedDoc.version} (자동 기록)</option>
                  <option>메신저로 받음 · 직접 선택</option>
                </select>
              </label>
            </div>
          ) : (
            <p className="mt-3 flex items-center gap-1.5 text-[11.5px] leading-relaxed text-foreground-500">
              <i className="ri-information-line text-[13px] text-primary-400" />새 문서는 파일명으로
              등록됩니다. 문서명과 기준 문서는 따로 입력하지 않습니다.
            </p>
          )}
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-background-700/60 pt-4">
          {error ? (
            <p className="flex items-center gap-1 text-[11.5px] text-red-300">
              <i className="ri-error-warning-line" /> 업로드에 실패했습니다. {error}
            </p>
          ) : (
            <p className="flex items-center gap-1 text-[11.5px] text-foreground-600">
              <i className="ri-info-card-line" /> 병합 셀·수식이 많은 XLSX는 추출 정확도가 낮을 수
              있습니다.
            </p>
          )}
          <button
            type="button"
            disabled={!file || submitting}
            onClick={onStart}
            className="ml-auto flex h-9 cursor-pointer items-center gap-1.5 whitespace-nowrap rounded-md bg-foreground-50 px-4 font-label text-[13px] font-medium text-background-950 transition hover:bg-foreground-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {submitting ? '업로드 중' : '분석 시작'}{' '}
            <i className="ri-arrow-right-line text-[13px]" />
          </button>
        </div>
      </section>

      <aside className="space-y-3">
        <div className="panel p-4">
          <h2 className="font-heading text-[15.5px] text-foreground-50">제출 전 확인</h2>
          <ul className="mt-3 space-y-2 text-[12.5px] leading-relaxed text-foreground-400">
            {CHECKLIST.map((item) => (
              <li key={item} className="flex gap-2">
                <i className="ri-check-line mt-0.5 text-primary-400" />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <div className="panel p-4">
          <h2 className="font-heading text-[15.5px] text-foreground-50">이 프로젝트의 문서</h2>
          <ul className="mt-2 divide-y divide-background-700/60">
            {documents.slice(0, PROJECT_DOC_PREVIEW).map((doc) => (
              <li key={doc.id} className="flex items-center justify-between gap-2 py-2">
                <span className="min-w-0 truncate text-[12.5px] text-foreground-300">
                  {doc.name}
                </span>
                <span className="flex shrink-0 items-center gap-1 font-label text-[11px] text-foreground-500">
                  v{doc.version}
                  {doc.pending && <span className="h-1.5 w-1.5 rounded-full bg-red-400" />}
                </span>
              </li>
            ))}
          </ul>
          <Link
            to="/documents"
            className="mt-2 flex cursor-pointer items-center gap-1 text-[12px] text-primary-300 hover:text-primary-200"
          >
            전체 보기 <i className="ri-arrow-right-line" />
          </Link>
        </div>
      </aside>
    </div>
  )
}

export default UploadStep
