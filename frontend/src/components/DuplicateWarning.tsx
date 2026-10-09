import { Link } from 'react-router'
import { STATUS_LABELS, type Duplicate, type DuplicateReason } from '../api/types'
import { formatShortDay, formatWon } from '../lib/format'
import { Icon } from './Icon'

const REASON: Record<DuplicateReason, string> = {
  SAME_IMAGE: '같은 사진',
  SIMILAR_IMAGE: '비슷한 사진',
  SAME_DETAILS: '가게·일시·금액 같음',
}

const describe = (d: Duplicate) =>
  [
    d.paid_at && formatShortDay(d.paid_at),
    d.store_name,
    d.total_amount != null && formatWon(d.total_amount),
    `${d.uploader_name} · ${STATUS_LABELS[d.status]}`,
  ]
    .filter(Boolean)
    .join(' · ')

/** 같은 영수증으로 보이는 다른 지출 (막지는 않고 알려만 줌). 볼 수 있는 지출이면 눌러서 이동 */
export function DuplicateWarning({
  orgId,
  duplicates,
  editable,
}: {
  orgId: number
  duplicates: Duplicate[]
  editable: boolean
}) {
  if (duplicates.length === 0) return null
  return (
    <div className="banner banner--warn anim-rise" role="note" style={{ alignItems: 'flex-start' }}>
      <Icon name="copy" size={20} style={{ marginTop: 1 }} />
      <span style={{ flex: 1, minWidth: 0 }}>
        이미 올라온 영수증 같아요
        {duplicates.map((d, index) =>
          d.expense_id !== null ? (
            <Link key={index} to={`/orgs/${orgId}/expenses/${d.expense_id}`} className="dup-line">
              {describe(d)} ({REASON[d.reason]})
            </Link>
          ) : (
            <span key={index} className="dup-line">
              {describe(d)} ({REASON[d.reason]})
            </span>
          ),
        )}
        <span className="dup-line" style={{ fontWeight: 600 }}>
          {editable ? '같은 영수증이면 이 지출은 삭제해 주세요' : '두 번 돌려주지 않게 확인하세요'}
        </span>
      </span>
    </div>
  )
}
