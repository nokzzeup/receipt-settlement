import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { Icon } from './Icon'

type Props = {
  title?: string
  /** 뒤로 가기 주소 (없으면 왼쪽 비움) */
  back?: string
  backLabel?: string
  /** 왼쪽 아이콘을 X로 (닫기) */
  close?: boolean
  right?: ReactNode
}

/** 화면 맨 위 줄: 뒤로/닫기 + 가운데 제목 + 오른쪽 버튼 (스크롤해도 위에 붙어 있음) */
export function TopBar({ title, back, backLabel, close = false, right }: Props) {
  return (
    <header className="topbar">
      {back ? (
        <Link className="icon-btn" to={back} aria-label={backLabel ?? (close ? '닫기' : '뒤로')}>
          <Icon name={close ? 'close' : 'chevronLeft'} />
        </Link>
      ) : (
        <span />
      )}
      <p className="topbar__title">{title}</p>
      {right ?? <span />}
    </header>
  )
}
