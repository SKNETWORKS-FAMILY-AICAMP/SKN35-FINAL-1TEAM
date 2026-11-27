import { queryOptions } from '@tanstack/react-query'

import { ApiError, request, tokenStorage } from './client'
import { getCompanyUsers, type CompanyUser } from './organizations'

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
