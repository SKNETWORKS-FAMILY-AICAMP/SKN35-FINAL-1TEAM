import { setupWorker } from 'msw/browser'

import { implementedHandlers, pendingHandlers } from './handlers'

// partial(기본): 백엔드에 없는 API 만 목업 / all: 전부 목업 (백엔드 없이 개발)
const handlers =
  import.meta.env.VITE_API_MOCKING === 'all'
    ? [...implementedHandlers, ...pendingHandlers]
    : pendingHandlers

export const worker = setupWorker(...handlers)
