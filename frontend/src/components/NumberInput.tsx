import { useState, type InputHTMLAttributes } from 'react'
import { formatNumber, parseInteger } from '../lib/format'

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'onChange' | 'inputMode'> & {
  value: string
  onValueChange: (value: string) => void
}

/**
 * 원 단위 정수 입력칸. 고치는 동안엔 입력한 그대로, 다른 데를 누르면 "25,400"처럼 쉼표를 넣어 보여준다.
 * 값(문자열)은 입력한 그대로 보관 → parseInteger 가 쉼표를 빼고 읽음
 */
export function NumberInput({ value, onValueChange, onFocus, onBlur, ...rest }: Props) {
  const [editing, setEditing] = useState(false)
  const parsed = parseInteger(value)
  const shown = !editing && typeof parsed === 'number' ? formatNumber(parsed) : value
  return (
    <input
      {...rest}
      inputMode="numeric"
      value={shown}
      onFocus={(e) => {
        setEditing(true)
        onFocus?.(e)
      }}
      onBlur={(e) => {
        setEditing(false)
        onBlur?.(e)
      }}
      onChange={(e) => onValueChange(e.target.value)}
    />
  )
}
