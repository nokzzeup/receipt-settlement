import { useEffect, useRef, useState } from 'react'

/** 폰 설정의 '동작 줄이기' */
export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true
}

/**
 * 숫자가 지난 값에서 새 값까지 부드럽게 바뀌게 (처음엔 0부터). 금액은 정수로만 표시.
 * '동작 줄이기'를 켰으면 바로 새 값.
 */
export function useCountUp(target: number, duration = 900): number {
  const [shown, setShown] = useState(0)
  const shownRef = useRef(0)

  useEffect(() => {
    const from = shownRef.current
    if (from === target) return
    const set = (value: number) => {
      shownRef.current = value
      setShown(value)
    }
    if (prefersReducedMotion()) {
      // 다음 프레임에 반영 (effect 안에서 바로 setState 하지 않게)
      const id = requestAnimationFrame(() => set(target))
      return () => cancelAnimationFrame(id)
    }
    const start = performance.now()
    let frame = 0
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - (1 - t) ** 3
      set(Math.round(from + (target - from) * eased))
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [target, duration])

  return shown
}
