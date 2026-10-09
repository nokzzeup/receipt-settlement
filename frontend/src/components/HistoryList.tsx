import type { CSSProperties } from 'react'
import { ACTION_LABELS, type ApprovalAction, type HistoryEntry } from '../api/types'
import { formatDateTime } from '../lib/format'
import { Icon, type IconName } from './Icon'

const LOOK: Record<ApprovalAction, { icon: IconName; tone?: 'ok' | 'danger' | 'done' }> = {
  SUBMIT: { icon: 'send' },
  WITHDRAW: { icon: 'undo' },
  APPROVE: { icon: 'check', tone: 'ok' },
  UNAPPROVE: { icon: 'undo' },
  REJECT: { icon: 'close', tone: 'danger' },
  REIMBURSE: { icon: 'wallet', tone: 'done' },
  UNREIMBURSE: { icon: 'undo' },
}

/** 제출·승인·반려·환급 기록 (오래된 것부터) */
export function HistoryList({ entries, style }: { entries: HistoryEntry[]; style?: CSSProperties }) {
  if (entries.length === 0) return null
  return (
    <section className="card anim-rise" style={style} aria-label="처리 기록">
      <h2 className="card__title">처리 기록</h2>
      <ol className="timeline">
        {entries.map((entry, index) => {
          const look = LOOK[entry.action]
          return (
            <li key={index} className="timeline__item">
              <span className={look.tone ? `timeline__dot timeline__dot--${look.tone}` : 'timeline__dot'}>
                <Icon name={look.icon} size={15} weight={2.2} />
              </span>
              <div className="timeline__body">
                <p className="timeline__title">
                  {ACTION_LABELS[entry.action]} · {entry.actor.name}
                </p>
                <p className="timeline__meta">{formatDateTime(entry.created_at)}</p>
                {entry.comment && <p className="timeline__comment">{entry.comment}</p>}
              </div>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
