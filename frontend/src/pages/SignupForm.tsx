import { useMutation } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'

import {
  companySignup,
  confirmEmailVerification,
  sendCompanyVerification,
  sendEmployeeVerification,
  signup,
  type EmailVerificationConfirmResponse,
} from '../api/auth'
import { errorMessage } from '../api/client'

export type SignupKind = 'employee' | 'company'
type Step = 'email' | 'code' | 'profile'

// backend/app/auth/schemas.py 의 검증 규칙과 맞춘다
const MAX_NAME_LENGTH = 50
const MIN_PASSWORD_LENGTH = 8
const MAX_PASSWORD_LENGTH = 128
const CODE_PATTERN = /^[0-9]{6}$/

const STEP_LABELS: { key: Step; label: string }[] = [
  { key: 'email', label: '메일 입력' },
  { key: 'code', label: '인증번호' },
  { key: 'profile', label: '정보 입력' },
]

const inputClass =
  'h-10 w-full rounded-md border border-background-600/70 bg-background-800/50 px-3 text-[12.5px] text-foreground-100 outline-none transition focus:border-primary-500/60 read-only:text-foreground-400'

interface SignupFormProps {
  kind: SignupKind
  // 가입 직후 자동 로그인 중인지
  loggingIn: boolean
  onComplete: (email: string, password: string) => void
}

function SignupForm({ kind, loggingIn, onComplete }: SignupFormProps) {
  const [step, setStep] = useState<Step>('email')
  const [companyName, setCompanyName] = useState('')
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [verified, setVerified] = useState<EmailVerificationConfirmResponse | null>(null)
  const [name, setName] = useState('')
  const [deptId, setDeptId] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirm, setPasswordConfirm] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const sendMutation = useMutation({
    mutationFn: () =>
      kind === 'company'
        ? sendCompanyVerification(companyName.trim(), email.trim())
        : sendEmployeeVerification(email.trim()),
    onSuccess: () => {
      setStep('code')
      setCode('')
      setError('')
      setNotice(`${email.trim()} 으로 인증번호를 보냈습니다.`)
    },
    onError: (err) =>
      setError(errorMessage(err, '인증번호를 보내지 못했습니다. 잠시 후 다시 시도해 주세요.')),
  })

  const confirmMutation = useMutation({
    mutationFn: () => confirmEmailVerification(email.trim(), code),
    onSuccess: (data) => {
      setVerified(data)
      setStep('profile')
      setError('')
      setNotice('')
    },
    onError: (err) =>
      setError(errorMessage(err, '인증번호를 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.')),
  })

  const signupMutation = useMutation({
    mutationFn: (token: string) =>
      kind === 'company'
        ? companySignup({ verification_token: token, name: name.trim(), password })
        : signup({
            verification_token: token,
            name: name.trim(),
            password,
            dept_id: Number(deptId),
          }),
    onSuccess: () => onComplete(verified!.email, password),
    onError: (err) =>
      setError(errorMessage(err, '가입하지 못했습니다. 잠시 후 다시 시도해 주세요.')),
  })

  const pending =
    sendMutation.isPending || confirmMutation.isPending || signupMutation.isPending || loggingIn

  // 메일을 바꾸거나 인증이 만료됐을 때 처음 단계로 돌아간다
  const restart = () => {
    setStep('email')
    setVerified(null)
    setCode('')
    setError('')
    setNotice('')
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()

    if (step === 'email') {
      if (kind === 'company' && !companyName.trim()) {
        setError('회사명을 입력해 주세요.')
        return
      }
      if (!email.includes('@')) {
        setError('회사 이메일을 입력해 주세요.')
        return
      }
      sendMutation.mutate()
      return
    }

    if (step === 'code') {
      if (!CODE_PATTERN.test(code)) {
        setError('메일로 받은 6자리 숫자를 입력해 주세요.')
        return
      }
      confirmMutation.mutate()
      return
    }

    if (!verified) return
    if (!name.trim() || name.trim().length > MAX_NAME_LENGTH) {
      setError(`이름을 ${MAX_NAME_LENGTH}자 이내로 입력해 주세요.`)
      return
    }
    if (kind === 'employee' && !deptId) {
      setError('부서를 선택해 주세요.')
      return
    }
    if (password.length < MIN_PASSWORD_LENGTH || password.length > MAX_PASSWORD_LENGTH) {
      setError(
        `비밀번호는 ${MIN_PASSWORD_LENGTH}자 이상 ${MAX_PASSWORD_LENGTH}자 이하로 입력해 주세요.`,
      )
      return
    }
    if (password !== passwordConfirm) {
      setError('비밀번호 확인이 일치하지 않습니다.')
      return
    }
    setError('')
    signupMutation.mutate(verified.verification_token)
  }

  const stepIndex = STEP_LABELS.findIndex((s) => s.key === step)
  const submitLabel =
    step === 'email'
      ? '인증번호 받기'
      : step === 'code'
        ? '인증 확인'
        : kind === 'company'
          ? '회사 등록하고 시작하기'
          : '가입하고 시작하기'

  return (
    <form onSubmit={handleSubmit} className="mt-5 space-y-3" noValidate>
      <ol className="flex items-center gap-2 font-label text-[10.5px]">
        {STEP_LABELS.map((s, i) => (
          <li
            key={s.key}
            className={`flex items-center gap-1.5 ${i <= stepIndex ? 'text-primary-300' : 'text-foreground-600'}`}
          >
            <span
              className={`flex h-4 w-4 items-center justify-center rounded-full border text-[9.5px] ${i <= stepIndex ? 'border-primary-500/60' : 'border-background-600'}`}
            >
              {i + 1}
            </span>
            {s.label}
            {i < STEP_LABELS.length - 1 && <span className="text-foreground-700">·</span>}
          </li>
        ))}
      </ol>

      {step === 'email' && (
        <>
          {kind === 'company' && (
            <label className="block">
              <span className="mb-1.5 block text-[10.5px] text-foreground-500">회사명</span>
              <input
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                maxLength={MAX_NAME_LENGTH}
                autoComplete="organization"
                className={inputClass}
              />
            </label>
          )}
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
        </>
      )}

      {step === 'code' && (
        <>
          <label className="block">
            <span className="mb-1.5 flex items-center justify-between text-[10.5px] text-foreground-500">
              회사 이메일
              <button
                type="button"
                onClick={restart}
                className="cursor-pointer text-primary-300 hover:text-primary-200"
              >
                변경
              </button>
            </span>
            <input value={email.trim()} readOnly className={inputClass} />
          </label>
          <label className="block">
            <span className="mb-1.5 flex items-center justify-between text-[10.5px] text-foreground-500">
              인증번호
              <button
                type="button"
                onClick={() => sendMutation.mutate()}
                disabled={pending}
                className="cursor-pointer text-primary-300 hover:text-primary-200 disabled:cursor-default disabled:text-foreground-600"
              >
                다시 받기
              </button>
            </span>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="6자리 숫자"
              className={`${inputClass} tracking-[0.3em]`}
            />
          </label>
        </>
      )}

      {step === 'profile' && verified && (
        <>
          <div className="rounded-md border border-background-600/70 bg-background-800/30 px-3 py-2 text-[11px] text-foreground-400">
            <p className="text-foreground-200">{verified.company_name ?? '회사'}</p>
            <p className="mt-0.5 font-label">{verified.email}</p>
          </div>
          <label className="block">
            <span className="mb-1.5 block text-[10.5px] text-foreground-500">이름</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={MAX_NAME_LENGTH}
              autoComplete="name"
              className={inputClass}
            />
          </label>
          {kind === 'employee' && (
            <label className="block">
              <span className="mb-1.5 block text-[10.5px] text-foreground-500">부서</span>
              <select
                value={deptId}
                onChange={(e) => setDeptId(e.target.value)}
                className={`${inputClass} cursor-pointer`}
              >
                <option value="">부서 선택</option>
                {verified.departments.map((dept) => (
                  <option key={dept.dept_id} value={dept.dept_id}>
                    {dept.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="block">
            <span className="mb-1.5 block text-[10.5px] text-foreground-500">
              비밀번호 ({MIN_PASSWORD_LENGTH}자 이상)
            </span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              className={inputClass}
            />
          </label>
          <label className="block">
            <span className="mb-1.5 block text-[10.5px] text-foreground-500">비밀번호 확인</span>
            <input
              type="password"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              autoComplete="new-password"
              className={inputClass}
            />
          </label>
        </>
      )}

      {notice && !error && (
        <p className="flex items-center gap-1.5 rounded-md border border-primary-500/30 bg-primary-500/10 px-2.5 py-2 text-[11px] text-primary-100">
          <i className="ri-mail-send-line text-[13px]" /> {notice}
        </p>
      )}
      {error && (
        <p className="flex items-center gap-1.5 rounded-md border border-red-400/30 bg-red-400/10 px-2.5 py-2 text-[11px] text-red-200">
          <i className="ri-error-warning-line text-[13px]" /> {error}
          {step === 'profile' && (
            <button
              type="button"
              onClick={restart}
              className="ml-auto shrink-0 cursor-pointer text-red-100 underline"
            >
              처음부터
            </button>
          )}
        </p>
      )}
      <button
        type="submit"
        disabled={pending}
        className="h-10 w-full cursor-pointer whitespace-nowrap rounded-md bg-foreground-50 font-label text-[12.5px] font-semibold text-background-950 transition hover:bg-foreground-100 disabled:cursor-default disabled:opacity-60"
      >
        {loggingIn ? '로그인 중…' : submitLabel}
      </button>
    </form>
  )
}

export default SignupForm
