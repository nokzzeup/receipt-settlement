/** 예산 막대: 승인된 집행액(진하게) + 승인 대기(빗금). 넘으면 빨강. 예산이 없으면 그리지 않음 */
export function BudgetMeter({
  budget,
  spent,
  awaiting,
  large = false,
  label,
}: {
  budget: number
  spent: number
  awaiting: number
  large?: boolean
  label: string
}) {
  const scale = Math.max(budget, spent + Math.max(awaiting, 0), 1)
  const pct = (value: number) => `${(Math.max(value, 0) / scale) * 100}%`
  const over = spent > budget
  const className = ['meter', large && 'meter--lg', over && 'meter--over'].filter(Boolean).join(' ')
  return (
    <div
      className={className}
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={budget}
      aria-valuenow={Math.max(spent, 0)}
    >
      <span className="meter__spent" style={{ width: pct(spent) }} />
      <span className="meter__awaiting" style={{ width: pct(awaiting) }} />
    </div>
  )
}
