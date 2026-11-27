const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
const TOKEN_KEY = 'accessToken'

// TODO: 새로고침 시 refresh 쿠키로 재발급하도록 바꾼 뒤 access 토큰은 메모리에만 보관
export const tokenStorage = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (token: string) => sessionStorage.setItem(TOKEN_KEY, token),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

// FastAPI 에러 응답 { detail } 에서 메시지만 꺼낸다
async function toApiError(res: Response) {
  const body = await res.text()
  try {
    const { detail } = JSON.parse(body) as { detail?: unknown }
    return new ApiError(res.status, typeof detail === 'string' ? detail : body)
  } catch {
    return new ApiError(res.status, body)
  }
}

function send(path: string, init?: RequestInit) {
  const token = tokenStorage.get()
  const isFormData = init?.body instanceof FormData

  return fetch(`${BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      ...(!isFormData && { 'Content-Type': 'application/json' }),
      ...(token && { Authorization: `Bearer ${token}` }),
      ...init?.headers,
    },
  })
}

let refreshing: Promise<boolean> | null = null

// refresh 토큰은 HttpOnly 쿠키라 본문 없이 호출. 동시에 여러 요청이 401 을 받아도 한 번만 재발급한다
function refreshAccessToken() {
  refreshing ??= send('/auth/refresh', { method: 'POST' })
    .then(async (res) => {
      if (!res.ok) return false
      const { access_token } = (await res.json()) as { access_token: string }
      tokenStorage.set(access_token)
      return true
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null
    })
  return refreshing
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res = await send(path, init)

  if (res.status === 401 && !path.startsWith('/auth/') && (await refreshAccessToken())) {
    res = await send(path, init)
  }
  if (!res.ok) {
    throw await toApiError(res)
  }
  if (res.status === 204) {
    return undefined as T
  }
  return res.json() as Promise<T>
}
