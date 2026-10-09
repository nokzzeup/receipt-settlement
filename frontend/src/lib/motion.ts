import type { CSSProperties } from 'react'

/** 순서대로 떠오르기: .anim-rise / .anim-fade 에 n번째 지연 (index.css 의 --i) */
export function stagger(index: number): CSSProperties {
  return { '--i': index } as CSSProperties
}
