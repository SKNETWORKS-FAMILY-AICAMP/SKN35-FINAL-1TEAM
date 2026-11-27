import { setupWorker } from 'msw/browser'

import { implementedHandlers, pendingHandlers } from './handlers'

// all: 전부 목업 (백엔드 없이 개발) / partial: 백엔드에 없는 API 만 목업
const handlers =
  import.meta.env.VITE_API_MOCKING === 'partial'
    ? pendingHandlers
    : [...implementedHandlers, ...pendingHandlers]

export const worker = setupWorker(...handlers)
