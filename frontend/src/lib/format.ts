// 금액·시간 표시 규칙: 금액은 원 단위 정수, 시간은 서버에서 UTC로 받고 화면에는 한국시간(Asia/Seoul)으로

const SEOUL = 'Asia/Seoul'

const wonFormat = new Intl.NumberFormat('ko-KR')
const dateTimeFormat = new Intl.DateTimeFormat('ko-KR', {
  timeZone: SEOUL,
  year: 'numeric',
  month: 'numeric',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})
const dateFormat = new Intl.DateTimeFormat('ko-KR', { timeZone: SEOUL, year: 'numeric', month: 'numeric', day: 'numeric' })
const inputParts = new Intl.DateTimeFormat('en-CA', {
  timeZone: SEOUL,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

/** 25400 → "25,400원" */
export function formatWon(amount: number): string {
  return `${wonFormat.format(amount)}원`
}

/** 25400 → "25,400" (단위는 따로 붙일 때) */
export function formatNumber(amount: number): string {
  return wonFormat.format(amount)
}

const dayKeyFormat = new Intl.DateTimeFormat('en-CA', { timeZone: SEOUL, year: 'numeric', month: '2-digit', day: '2-digit' })

/** 한국 날짜 기준 하루 구분 값 "2026-10-09" */
export function seoulDayKey(date: string | Date): string {
  return dayKeyFormat.format(typeof date === 'string' ? new Date(date) : date)
}

/**
 * 목록 날짜 머리말 (한국 날짜 기준): "오늘 · 10월 9일" / "어제 · 10월 8일" / "10월 7일" / "2025년 12월 3일"
 * 한국은 서머타임이 없어서 '어제' = 지금부터 24시간 전의 한국 날짜
 */
export function formatDayLabel(iso: string, now: Date = new Date()): string {
  const key = seoulDayKey(iso)
  const [year, month, day] = key.split('-').map(Number)
  const monthDay = `${month}월 ${day}일`
  if (key === seoulDayKey(now)) return `오늘 · ${monthDay}`
  if (key === seoulDayKey(new Date(now.getTime() - 24 * 60 * 60 * 1000))) return `어제 · ${monthDay}`
  return year === Number(seoulDayKey(now).slice(0, 4)) ? monthDay : `${year}년 ${monthDay}`
}

/** 짧은 날짜: "오늘" / "어제" / "10월 7일" */
export function formatShortDay(iso: string, now: Date = new Date()): string {
  return formatDayLabel(iso, now).split(' · ')[0]
}

/** "2026-09-28T05:32:05Z" → "2026. 9. 28. 14:32" (한국시간) */
export function formatDateTime(iso: string | null | undefined): string {
  return iso ? dateTimeFormat.format(new Date(iso)) : ''
}

/** "2026-09-28T05:32:05Z" → "2026. 9. 28." (한국시간) */
export function formatDate(iso: string | null | undefined): string {
  return iso ? dateFormat.format(new Date(iso)) : ''
}

/** 서버 시각(ISO) → <input type="datetime-local"> 값 "2026-09-28T14:32" (한국시간, 분 단위) */
export function toSeoulInput(iso: string | null | undefined): string {
  if (!iso) return ''
  const p = Object.fromEntries(inputParts.formatToParts(new Date(iso)).map((part) => [part.type, part.value]))
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`
}

/** datetime-local 값(한국시간) → 시간대 포함 ISO. 한국은 서머타임이 없어서 항상 +09:00 */
export function fromSeoulInput(value: string): string | null {
  if (!value) return null
  return `${value.length === 16 ? `${value}:00` : value}+09:00`
}

/**
 * 입력칸 문자열 → 정수. 빈칸이면 null, 정수가 아니면 undefined (float 금지 규칙)
 *   "1,200" → 1200 / "" → null / "12.5" → undefined
 */
export function parseInteger(value: string): number | null | undefined {
  const text = value.replaceAll(',', '').trim()
  if (text === '') return null
  if (!/^-?\d+$/.test(text)) return undefined
  const number = Number(text)
  return Number.isSafeInteger(number) ? number : undefined
}
