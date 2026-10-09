import type { CSSProperties } from 'react'
import type { IconName } from '../components/Icon'

/**
 * 계정과목 → 아이콘·색. 계정과목은 조직마다 이름을 자유롭게 정하므로 이름에 든 낱말로 고른다.
 * 기본 계정과목(backend app/classify/defaults.py: 식비, 간식·음료, 비품·소모품, 인쇄·홍보, 교통비, 기타)은 모두 걸리게.
 * 못 고르면 id로 색을 돌려가며 쓴다 (같은 계정과목은 항상 같은 색).
 */
export type CategoryLook = {
  icon: IconName
  /** 아이콘 타일 바탕 */
  bg: string
  /** 아이콘 색 */
  fg: string
  /** 같은 바탕 위 글자 색 (대비 4.5:1 이상) */
  text: string
}

const LOOKS = {
  food: { icon: 'food', bg: '#fff0e5', fg: '#e8590c', text: '#b4470a' },
  snack: { icon: 'cup', bg: '#fef6dc', fg: '#a87203', text: '#8a5a00' },
  supplies: { icon: 'box', bg: '#e6f7f4', fg: '#0b8a73', text: '#0a6e5c' },
  print: { icon: 'print', bg: '#e0f5fa', fg: '#0891b2', text: '#0e7490' },
  transport: { icon: 'bus', bg: '#e8f1ff', fg: '#2563eb', text: '#1d4ed8' },
  event: { icon: 'party', bg: '#fcebf6', fg: '#c2255c', text: '#a61e4d' },
  study: { icon: 'book', bg: '#eef6e3', fg: '#4d7c0f', text: '#3f6212' },
  etc: { icon: 'dots', bg: '#eef0f3', fg: '#5f6672', text: '#4a515c' },
} satisfies Record<string, CategoryLook>

const KEYWORDS: [keyof typeof LOOKS, string[]][] = [
  ['snack', ['간식', '음료', '커피', '카페', '다과', '음료수']],
  ['food', ['식비', '식대', '식사', '음식', '회식', '밥', '도시락']],
  ['supplies', ['비품', '소모품', '물품', '문구', '용품', '장비']],
  ['print', ['인쇄', '홍보', '현수막', '포스터', '출력', '디자인']],
  ['transport', ['교통', '택시', '버스', '주차', '유류', '기차', '이동']],
  ['event', ['행사', '축제', '이벤트', '대회', '공연', '상품', '경품']],
  ['study', ['도서', '교재', '학술', '세미나', '교육', '스터디']],
  ['etc', ['기타']],
]

const FALLBACK: CategoryLook[] = [
  { icon: 'tag', bg: '#e8f1ff', fg: '#2563eb', text: '#1d4ed8' },
  { icon: 'tag', bg: '#e6f7f4', fg: '#0b8a73', text: '#0a6e5c' },
  { icon: 'tag', bg: '#fff0e5', fg: '#e8590c', text: '#b4470a' },
  { icon: 'tag', bg: '#fcebf6', fg: '#c2255c', text: '#a61e4d' },
  { icon: 'tag', bg: '#e0f5fa', fg: '#0891b2', text: '#0e7490' },
]

/** 계정과목이 없거나(미분류) 모를 때 */
export const NO_CATEGORY: CategoryLook = { icon: 'receipt', bg: '#eef0f3', fg: '#5f6672', text: '#4a515c' }

export function categoryLook(category: { id: number; name: string } | null | undefined): CategoryLook {
  if (!category) return NO_CATEGORY
  const found = KEYWORDS.find(([, words]) => words.some((word) => category.name.includes(word)))
  return found ? LOOKS[found[0]] : FALLBACK[category.id % FALLBACK.length]
}

/** .tile 에 넣을 색 변수 */
export function tileStyle(look: CategoryLook): CSSProperties {
  return { '--tile-bg': look.bg, '--tile-fg': look.fg } as CSSProperties
}

/** .cat-chip 에 넣을 색 변수 */
export function chipStyle(look: CategoryLook): CSSProperties {
  return { '--chip-bg': look.bg, '--chip-fg': look.text } as CSSProperties
}
