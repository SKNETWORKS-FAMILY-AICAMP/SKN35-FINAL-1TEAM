import { useMutation } from '@tanstack/react-query'
import { useEffect, useRef, useState, type FormEvent } from 'react'

import { askAssistant, type AnswerSource } from '../api/assistant'
import Badge from '../components/Badge'
import { useCurrentUser } from '../hooks/useAuth'

interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  sources?: AnswerSource[]
}

const SAMPLE_QUESTIONS = [
  '현재 무료배송 기준은?',
  '지난주에 쇼핑몰 기획 뭐 바뀌었어?',
  '이 변경이 우리 팀에 영향 있어?',
  '내가 아직 확인 안 한 거 있어?',
  '장바구니 화면설계서 최신본 줘',
]
const QUICK_QUESTION_COUNT = 3

const ANSWER_RULES = [
  '승인된 HEAD 문서만 검색합니다.',
  '팀 내부 문서는 해당 팀에만 답합니다.',
  '출처를 댈 수 없으면 답하지 않습니다.',
  '열람 권한은 DB 규칙으로 판정합니다.',
]

function BotAvatar({ className = '' }: { className?: string }) {
  return (
    <span
      className={`flex h-7 w-7 items-center justify-center rounded-full border border-primary-500/25 bg-primary-500/10 text-primary-300 ${className}`}
    >
      <i className="ri-brain-line text-[14px]" />
    </span>
  )
}

function AssistantPage() {
  const { user: me } = useCurrentUser()
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Message[]>([])
  const endRef = useRef<HTMLDivElement>(null)

  const greeting: Message = {
    id: 'greeting',
    role: 'assistant',
    text: `안녕하세요, ${me.name}님. 승인된 HEAD 문서만 근거로 답합니다. 권한이 없는 문서는 검색 단계에서 제외되고, 모든 답변에 문서명·버전·구간 출처를 붙입니다.`,
  }

  const ask = useMutation({
    mutationFn: askAssistant,
    onSuccess: (answer) =>
      setMessages((prev) => [
        ...prev,
        { id: `a-${Date.now()}`, role: 'assistant', text: answer.text, sources: answer.sources },
      ]),
  })

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, ask.isPending])

  const send = (question: string) => {
    const q = question.trim()
    if (!q || ask.isPending) return
    setInput('')
    setMessages((prev) => [...prev, { id: `u-${Date.now()}`, role: 'user', text: q }])
    ask.mutate(q)
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    send(input)
  }

  return (
    <div className="space-y-4 pb-12">
      <section className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="overline">SHOP · 쇼핑몰 구축 · 어시스턴트</p>
          <h1 className="mt-3 font-heading text-[28px] leading-tight text-foreground-50 md:text-[34px]">
            <span className="font-semibold">기준 문서</span>{' '}
            <span className="font-light text-foreground-200">어시스턴트</span>
          </h1>
          <p className="mt-2 max-w-2xl text-[14px] leading-relaxed text-foreground-400">
            “어떤 게 최신이야?”를 묻지 않아도 됩니다. 승인 대기 제출본은 검색하지 않고, 열람 권한
            범위 안에서만 답합니다.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge tone="accent" icon="ri-shield-check-line">
            권한 필터 적용
          </Badge>
          <Badge tone="primary" icon="ri-links-line">
            MCP 연동 가능
          </Badge>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_300px]">
        <section className="panel flex h-[calc(100vh-290px)] min-h-[520px] flex-col overflow-hidden">
          <div className="flex items-center justify-between border-b border-background-700/60 px-4 py-2.5">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-sm text-primary-300">
                <i className="ri-sparkling-2-line text-[14px]" />
              </span>
              <p className="text-[13px] text-foreground-200">LangGraph 질의 응답 에이전트</p>
            </div>
            <span className="flex items-center gap-1.5 font-label text-[11px] uppercase tracking-[0.14em] text-foreground-600">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-400" /> head only
            </span>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
            {[greeting, ...messages].map((message) =>
              message.role === 'assistant' ? (
                <div key={message.id} className="flex gap-2.5">
                  <BotAvatar className="shrink-0" />
                  <div className="min-w-0 max-w-[92%]">
                    <p className="rounded-lg rounded-tl-sm border border-background-700/70 bg-background-800/50 px-3.5 py-3 text-[13.5px] leading-[1.75] text-foreground-200">
                      {message.text}
                    </p>
                    {!!message.sources?.length && (
                      <div className="mt-2 space-y-1.5">
                        <p className="font-label text-[10.5px] uppercase tracking-[0.16em] text-foreground-600">
                          출처
                        </p>
                        {message.sources.map((source) => (
                          <div
                            key={`${source.doc}-${source.section}`}
                            className="flex flex-wrap items-center gap-1.5 rounded-md border border-background-700/70 bg-background-900/60 px-2.5 py-1.5"
                          >
                            <i className="ri-file-text-line text-[13px] text-primary-400" />
                            <span className="text-[12px] text-foreground-200">{source.doc}</span>
                            <span className="rounded-sm px-1.5 py-0.5 font-label text-[10.5px] text-primary-300">
                              {source.version}
                            </span>
                            <span className="text-[11.5px] text-foreground-500">
                              {source.section}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div key={message.id} className="flex justify-end gap-2.5">
                  <p className="max-w-[80%] rounded-lg rounded-tr-sm border border-primary-500/25 bg-primary-500/10 px-3.5 py-2.5 text-[13.5px] leading-relaxed text-foreground-100">
                    {message.text}
                  </p>
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-background-600 bg-background-800 text-[11px] text-foreground-300">
                    {me.name.slice(0, 1)}
                  </span>
                </div>
              ),
            )}

            {ask.isPending && (
              <div className="flex items-center gap-2.5">
                <BotAvatar />
                <span className="flex items-center gap-1 rounded-lg border border-background-700/70 bg-background-800/50 px-3 py-2.5">
                  {[0, 1, 2].map((i) => (
                    <span
                      key={i}
                      className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-primary-400"
                      style={{ animationDelay: `${i * 160}ms` }}
                    />
                  ))}
                </span>
              </div>
            )}
            <div ref={endRef} />
          </div>

          <div className="border-t border-background-700/60 p-3">
            <div className="mb-2 flex flex-wrap gap-1.5">
              {SAMPLE_QUESTIONS.slice(0, QUICK_QUESTION_COUNT).map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => send(q)}
                  className="cursor-pointer whitespace-nowrap rounded-full border border-background-600/70 px-2.5 py-1 text-[11.5px] text-foreground-400 transition hover:border-primary-500/40 hover:text-primary-200"
                >
                  {q}
                </button>
              ))}
            </div>
            <form onSubmit={handleSubmit} className="flex items-center gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="기준 문서에 대해 물어보세요 (예: 현재 무료배송 기준은?)"
                className="h-10 flex-1 rounded-md border border-background-600/70 bg-background-800/50 px-3 text-[13.5px] text-foreground-100 outline-none transition placeholder:text-foreground-600 focus:border-primary-500/60"
              />
              <button
                type="submit"
                disabled={!input.trim() || ask.isPending}
                aria-label="질문 보내기"
                className="flex h-10 w-10 shrink-0 cursor-pointer items-center justify-center rounded-md bg-primary-500 text-background-950 transition hover:bg-primary-400 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <i className="ri-arrow-up-line text-[16px]" />
              </button>
            </form>
          </div>
        </section>

        <aside className="space-y-3">
          <div className="panel p-4">
            <h2 className="font-heading text-[15px] text-foreground-50">답변 규칙</h2>
            <ul className="mt-3 space-y-2 text-[12px] leading-relaxed text-foreground-400">
              {ANSWER_RULES.map((rule) => (
                <li key={rule} className="flex gap-1.5">
                  <i className="ri-check-line mt-0.5 text-primary-400" />
                  {rule}
                </li>
              ))}
            </ul>
          </div>

          <div className="panel p-4">
            <h2 className="font-heading text-[15px] text-foreground-50">질문 예시</h2>
            <div className="mt-2.5 space-y-1.5">
              {SAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => send(q)}
                  className="flex w-full cursor-pointer items-center justify-between gap-2 rounded-sm border border-background-700/70 px-2.5 py-2 text-left text-[12px] text-foreground-300 transition hover:border-primary-500/40 hover:text-primary-200"
                >
                  <span className="truncate">{q}</span>
                  <i className="ri-arrow-right-up-line shrink-0 text-[12px]" />
                </button>
              ))}
            </div>
          </div>

          <div className="panel p-4">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-sm border border-background-600 text-foreground-400">
                <i className="ri-plug-2-line text-[13px]" />
              </span>
              <h2 className="font-heading text-[15px] text-foreground-50">MCP로 쓰기</h2>
            </div>
            <p className="mt-2 text-[11.5px] leading-relaxed text-foreground-500">
              Cursor·Claude Code에서 개인 토큰으로 HEAD 문서를 조회합니다. 게스트는 사용할 수 없고,
              모든 조회는 감사 로그에 남습니다.
            </p>
            {/* TODO: MCP 개인 토큰 발급 API 연결 */}
            <button
              type="button"
              className="mt-2.5 h-8 w-full cursor-pointer whitespace-nowrap rounded-md border border-background-600/80 font-label text-[12px] text-foreground-200 transition hover:border-primary-500/40 hover:text-primary-200"
            >
              토큰 발급
            </button>
          </div>
        </aside>
      </div>
    </div>
  )
}

export default AssistantPage
