import { useCallback, useEffect, useRef, useState } from 'react'

const TOAST_DURATION_MS = 2600

export function useToast() {
  const [message, setMessage] = useState('')
  const timer = useRef<number | undefined>(undefined)

  const show = useCallback((next: string) => {
    window.clearTimeout(timer.current)
    setMessage(next)
    timer.current = window.setTimeout(() => setMessage(''), TOAST_DURATION_MS)
  }, [])

  useEffect(() => () => window.clearTimeout(timer.current), [])

  return { message, show }
}
