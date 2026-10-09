import type { CSSProperties } from 'react'

export type Segment<K extends string> = { key: K; label: string; count?: number }

type Props<K extends string> = {
  segments: Segment<K>[]
  value: K
  onChange: (key: K) => void
  label: string
}

/** 회색 칸 안에서 흰 표시가 미끄러지는 탭 (목록 거르기 등) */
export function SegmentedTabs<K extends string>({ segments, value, onChange, label }: Props<K>) {
  const index = Math.max(
    0,
    segments.findIndex((s) => s.key === value),
  )
  const style = { '--count': segments.length, '--index': index } as CSSProperties
  return (
    <div className="segmented" style={style} role="group" aria-label={label}>
      <span className="segmented__indicator" aria-hidden="true" />
      {segments.map((segment) => (
        <button
          key={segment.key}
          type="button"
          className="segmented__item"
          aria-pressed={segment.key === value}
          onClick={() => onChange(segment.key)}
        >
          {segment.label}
          {segment.count !== undefined && <span className="segmented__count">{segment.count}</span>}
        </button>
      ))}
    </div>
  )
}
