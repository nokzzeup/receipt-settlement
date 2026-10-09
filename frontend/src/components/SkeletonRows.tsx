/** 목록을 불러오는 동안 보여주는 반짝이는 회색 줄 */
export function SkeletonRows({ count }: { count: number }) {
  return (
    <div className="skeleton-rows" aria-hidden="true">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="skeleton-row">
          <span className="skeleton" style={{ width: 44, height: 44, borderRadius: 14, flex: 'none' }} />
          <span style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <span className="skeleton" style={{ width: '55%', height: 14 }} />
            <span className="skeleton" style={{ width: '35%', height: 12 }} />
          </span>
        </div>
      ))}
    </div>
  )
}
