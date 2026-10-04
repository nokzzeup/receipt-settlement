import type { ReactNode } from 'react'

type PageProps = {
  title: string
  /** 아직 안 만든 부분 메모 (빈 화면 단계용) */
  todo?: string
  children?: ReactNode
}

/** 화면 공통 틀: 제목 + (임시) TODO 메모 + 내용 */
export function Page({ title, todo, children }: PageProps) {
  return (
    <section className="page">
      <h1 className="page__title">{title}</h1>
      {todo && <p className="page__todo">{todo}</p>}
      {children}
    </section>
  )
}
