import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router'

import { ApiError } from '../api/client'
import { useLogin } from '../hooks/useAuth'

type AuthMode = 'login' | 'signup'

const AUTH_TABS: { key: AuthMode; label: string }[] = [
  { key: 'login', label: '로그인' },
  { key: 'signup', label: '첫 로그인 · 가입' },
]

const FEATURES = [
  {
    icon: 'ri-file-shield-2-line',
    title: '승인된 문서만 HEAD',
    desc: '버전은 문서마다 따로, 롤백과 기준선까지',
  },
  {
    icon: 'ri-user-shared-line',
    title: 'AI가 영향 팀을 먼저 제안',
    desc: '제출자는 불필요한 팀만 덜어냅니다',
  },
  {
    icon: 'ri-check-double-line',
    title: '확인까지 추적',
    desc: '미확인 빨간 점, 2일 리마인드, 팀별 현황',
  },
]

// MSW 전체 목업 모드에서만 노출하는 테스트 계정 (src/mocks/data.ts 와 같은 값)
const SHOW_DEMO_ACCOUNTS =
  import.meta.env.DEV && (import.meta.env.VITE_API_MOCKING ?? 'all') === 'all'
const DEMO_PASSWORD = 'brain2026!'
const DEMO_ACCOUNTS = [
  { email: 'gildong.hong@hedy.co.kr', name: '홍길동', team: '기획팀', role: '팀원' },
  { email: 'minjun.kim@hedy.co.kr', name: '김민준', team: 'PMO', role: '승인권자' },
  { email: 'seoyeon.park@hedy.co.kr', name: '박서연', team: '주문·결제 개발', role: '팀원' },
]

const MIN_PASSWORD_LENGTH = 6

const inputClass =
  'h-10 w-full rounded-md border border-background-600/70 bg-background-800/50 px-3 text-[12.5px] text-foreground-100 outline-none transition focus:border-primary-500/60'

function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const loginMutation = useLogin()
  const [mode, setMode] = useState<AuthMode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  const redirectTo = (location.state as { from?: string } | null)?.from ?? '/dashboard'

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!email.includes('@') || password.length < MIN_PASSWORD_LENGTH) {
      setError('회사 이메일과 6자 이상의 비밀번호를 입력해 주세요.')
      return
    }
    if (mode === 'signup') {
      setError('가입은 백엔드 연결 후 사용할 수 있습니다.')
      return
    }
    setError('')
    loginMutation.mutate(
      { email, password },
      {
        onSuccess: () => navigate(redirectTo, { replace: true }),
        onError: (err) =>
          setError(
            err instanceof ApiError && err.status === 401
              ? '이메일 또는 비밀번호가 올바르지 않습니다.'
              : '로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.',
          ),
      },
    )
  }

  const fillDemoAccount = (demoEmail: string) => {
    setMode('login')
    setEmail(demoEmail)
    setPassword(DEMO_PASSWORD)
    setError('')
  }

  return (
    <div className="relative flex min-h-screen flex-col">
      <header className="flex h-16 items-center justify-between px-4 md:px-10">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-md border border-primary-500/30 bg-primary-500/10 text-primary-400">
            <i className="ri-brain-line text-base" />
          </span>
          <div>
            <p className="font-heading text-[14px] font-semibold leading-none text-foreground-50">
              헤디
            </p>
            <p className="mt-1 font-label text-[9.5px] uppercase tracking-[0.2em] text-foreground-500">
              hedy
            </p>
          </div>
        </div>
        <p className="font-label text-[10px] uppercase tracking-[0.18em] text-foreground-600">
          mockup · 2026.11
        </p>
      </header>

      <main className="mx-auto grid w-full max-w-[1120px] flex-1 grid-cols-1 items-center gap-10 px-4 py-8 md:px-10 lg:grid-cols-2 lg:gap-16">
        <section className="hidden lg:block">
          <p className="overline">변경 전파 누락을 없애는 한 곳</p>
          <h1 className="mt-4 font-heading text-[44px] leading-[1.12] text-foreground-50">
            <span className="font-semibold">확정</span>은 여기서,
            <br />
            <span className="font-light text-foreground-200">전달</span>은 자동으로.
          </h1>
          <p className="mt-4 max-w-md text-[13.5px] leading-[1.85] text-foreground-400">
            팀 안 작업은 원래 쓰던 도구에서 그대로. 확정하려는 산출물만 한 번 올리면, 승인된 문서가
            기준(HEAD)이 되고 영향받는 팀에 검증된 3줄 요약이 먼저 도착합니다.
          </p>
          <div className="mt-8 space-y-3">
            {FEATURES.map((feature) => (
              <div key={feature.title} className="flex items-start gap-3">
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-background-600/70 bg-background-800/50 text-primary-300">
                  <i className={`${feature.icon} text-[15px]`} />
                </span>
                <div>
                  <p className="text-[12.5px] text-foreground-100">{feature.title}</p>
                  <p className="mt-0.5 text-[11px] text-foreground-500">{feature.desc}</p>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-8 border-l-2 border-primary-500/40 pl-3 text-[11.5px] leading-relaxed text-foreground-500">
            상대에게 먼저 알려주는 push 방식. 사람이 물어봐야 답하는 검색 도구와 다릅니다.
          </p>
        </section>

        <section className="panel mx-auto w-full max-w-[400px] p-6 shadow-panel md:p-7">
          <div className="flex h-9 items-center rounded-md border border-background-600/70 bg-background-800/40 p-1">
            {AUTH_TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setMode(tab.key)}
                className={`h-full flex-1 cursor-pointer whitespace-nowrap rounded-full font-label text-[11.5px] transition ${mode === tab.key ? 'bg-foreground-50 text-background-950' : 'text-foreground-400 hover:text-foreground-100'}`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <h2 className="mt-5 font-heading text-[20px] text-foreground-50">
            {mode === 'login' ? '프로젝트로 돌아가기' : '워크스페이스 만들기'}
          </h2>
          <p className="mt-1 text-[11.5px] leading-relaxed text-foreground-500">
            {mode === 'login'
              ? '회사 이메일로 로그인하면 참여 중인 프로젝트만 보입니다.'
              : '가입 후 관리자가 프로젝트와 팀을 배정합니다.'}
          </p>

          <form onSubmit={handleSubmit} className="mt-5 space-y-3" noValidate>
            <label className="block">
              <span className="mb-1.5 block text-[10.5px] text-foreground-500">회사 이메일</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                className={inputClass}
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-[10.5px] text-foreground-500">비밀번호</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                className={inputClass}
              />
            </label>
            {mode === 'signup' && (
              <label className="block">
                <span className="mb-1.5 block text-[10.5px] text-foreground-500">회사명</span>
                <input defaultValue="헤디" className={inputClass} />
              </label>
            )}
            {error && (
              <p className="flex items-center gap-1.5 rounded-md border border-red-400/30 bg-red-400/10 px-2.5 py-2 text-[11px] text-red-200">
                <i className="ri-error-warning-line text-[13px]" /> {error}
              </p>
            )}
            <button
              type="submit"
              disabled={loginMutation.isPending}
              className="h-10 w-full cursor-pointer whitespace-nowrap rounded-md bg-foreground-50 font-label text-[12.5px] font-semibold text-background-950 transition hover:bg-foreground-100"
            >
              {mode === 'login' ? '로그인' : '가입하고 시작하기'}
            </button>
          </form>

          {SHOW_DEMO_ACCOUNTS && (
            <div className="mt-5">
              <p className="font-label text-[10.5px] uppercase tracking-[0.18em] text-foreground-600">
                데모 계정
              </p>
              <div className="mt-2 space-y-1.5">
                {DEMO_ACCOUNTS.map((account) => (
                  <button
                    key={account.email}
                    type="button"
                    onClick={() => fillDemoAccount(account.email)}
                    className={`flex w-full cursor-pointer items-center justify-between gap-2 rounded-md border px-3 py-2 text-left transition ${email === account.email ? 'border-primary-500/50 bg-primary-500/10' : 'border-background-600/70 hover:border-background-500 hover:bg-background-800/60'}`}
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-[12px] text-foreground-100">
                        {account.name} · {account.team}
                      </span>
                      <span className="block truncate font-label text-[10.5px] text-foreground-500">
                        {account.email}
                      </span>
                    </span>
                    <span className="shrink-0 rounded-full border border-background-600/70 px-2 py-0.5 font-label text-[10.5px] text-foreground-300">
                      {account.role}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="mt-5 border-t border-background-700/60 pt-4">
            <p className="flex items-center gap-1.5 text-[10.5px] leading-relaxed text-foreground-500">
              <i className="ri-information-line text-[12px] text-primary-400" />
              게스트(고객사)는 초대받은 프로젝트의 ‘외부 공유’ 문서만 열람합니다.
            </p>
            <p className="mt-2 text-[10px] text-foreground-600">
              이 화면은 발표용 목업입니다. 실제 가입·인증은 백엔드 연결 후 동작합니다.
            </p>
          </div>
        </section>
      </main>
    </div>
  )
}

export default LoginPage
