import { queryOptions } from '@tanstack/react-query'

import { ApiError, request, tokenStorage } from './client'
import { getCompanyUsers, type CompanyUser, type Department } from './organizations'

// backend/app/auth/schemas.py 의 LoginRequest, TokenResponse
export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export function login(body: LoginRequest) {
  return request<TokenResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function logout() {
  return request<void>('/auth/logout', { method: 'POST' })
}

// backend/app/auth/schemas.py 의 가입 관련 요청·응답
export type VerificationPurpose = 'COMPANY_REGISTER' | 'EMPLOYEE_SIGNUP'

export interface EmailVerificationConfirmResponse {
  verification_token: string
  email: string
  purpose: VerificationPurpose
  company_name: string | null
  // 직원 가입일 때만 채워진다
  departments: Department[]
}

export interface SignupRequest {
  verification_token: string
  password: string
  name: string
  dept_id: number
}

export interface CompanyRegisterRequest {
  verification_token: string
  name: string
  password: string
}

export function sendCompanyVerification(companyName: string, email: string) {
  return request<void>('/auth/company-email-verifications', {
    method: 'POST',
    body: JSON.stringify({ company_name: companyName, email }),
  })
}

export function sendEmployeeVerification(email: string) {
  return request<void>('/auth/email-verifications', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

export function confirmEmailVerification(email: string, code: string) {
  return request<EmailVerificationConfirmResponse>('/auth/email-verifications/confirm', {
    method: 'POST',
    body: JSON.stringify({ email, code }),
  })
}

export function signup(body: SignupRequest) {
  return request<unknown>('/auth/signup', { method: 'POST', body: JSON.stringify(body) })
}

export function companySignup(body: CompanyRegisterRequest) {
  return request<unknown>('/auth/company-signup', { method: 'POST', body: JSON.stringify(body) })
}

// access 토큰의 sub 가 user_id. 화면 표시용으로만 읽고 검증은 백엔드가 한다
function getUserIdFromToken(token: string) {
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const { sub } = JSON.parse(atob(payload)) as { sub?: string }
    return sub ? Number(sub) : null
  } catch {
    return null
  }
}

// TODO: 백엔드에 내 정보 조회(/users/me) API 가 생기면 교체
async function fetchMe(): Promise<CompanyUser> {
  const userId = getUserIdFromToken(tokenStorage.get() ?? '')
  const { users } = await getCompanyUsers()
  const me = users.find((u) => u.user_id === userId)
  if (!me) throw new ApiError(401, '다시 로그인 해주세요.')
  return me
}

export const authQueries = {
  me: () =>
    queryOptions({
      queryKey: ['me'],
      queryFn: fetchMe,
      staleTime: Infinity,
      retry: false,
    }),
}
