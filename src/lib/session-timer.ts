import { useEffect, useRef, useState, useCallback } from 'react'

const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000 // 30 minutes

/**
 * Detects user inactivity and returns whether the idle warning is showing.
 * Resets on any user interaction (mouse, keyboard, scroll, touch).
 */
export function useInactivityWarning(timeoutMs: number = INACTIVITY_TIMEOUT_MS): boolean {
  const [isIdle, setIsIdle] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const resetTimer = useCallback(() => {
    setIsIdle(false)
    if (timerRef.current) clearTimeout(timerRef.current)
    timerRef.current = setTimeout(() => setIsIdle(true), timeoutMs)
  }, [timeoutMs])

  useEffect(() => {
    const events = ['mousemove', 'keydown', 'scroll', 'touchstart'] as const
    for (const event of events) {
      window.addEventListener(event, resetTimer, { passive: true })
    }
    resetTimer()

    return () => {
      for (const event of events) {
        window.removeEventListener(event, resetTimer)
      }
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [resetTimer])

  return isIdle
}
