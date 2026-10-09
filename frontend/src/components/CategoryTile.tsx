import { categoryLook, tileStyle } from '../lib/categoryStyle'
import { Icon } from './Icon'

type Props = {
  category: { id: number; name: string } | null | undefined
  size?: 'sm' | 'md' | 'lg'
}

const ICON_SIZE = { sm: 17, md: 20, lg: 22 } as const

/** 계정과목 색 타일 + 아이콘 (없으면 회색 영수증) */
export function CategoryTile({ category, size = 'lg' }: Props) {
  const look = categoryLook(category)
  const sizeClass = size === 'lg' ? 'tile' : `tile tile--${size}`
  return (
    <span className={sizeClass} style={tileStyle(look)} aria-hidden="true">
      <Icon name={look.icon} size={ICON_SIZE[size]} />
    </span>
  )
}
