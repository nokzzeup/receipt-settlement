import type { ReactNode } from 'react'

type LargeTitleProps = {
  title: string
  subtitle?: ReactNode
}

/** 화면 위쪽 큰 제목 (+ 설명 한 줄) */
export function LargeTitle({ title, subtitle }: LargeTitleProps) {
  return (
    <div className="large-title anim-rise">
      <h1>{title}</h1>
      {subtitle && <p>{subtitle}</p>}
    </div>
  )
}

type PageProps = {
  title: string
  subtitle?: ReactNode
  children?: ReactNode
}

/** 단순한 화면 틀 (오류·빈 화면 등): 위 여백 + 큰 제목 + 내용 */
export function Page({ title, subtitle, children }: PageProps) {
  return (
    <div className="screen" style={{ paddingTop: 56 }}>
      <LargeTitle title={title} subtitle={subtitle} />
      {children}
    </div>
  )
}
