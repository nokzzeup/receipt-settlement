import { useState } from 'react'
import { createPortal } from 'react-dom'
import { errorMessage } from '../api/client'
import { useExpenseAction, type ExpenseAction } from '../api/expenses'
import type { ExpenseDetail } from '../api/types'
import { useFeedback } from '../feedback/context'
import { formatWon } from '../lib/format'
import { BottomSheet } from './BottomSheet'
import { Icon } from './Icon'

const QUICK_REASONS = ['영수증이 잘 안 보여요', '조직 지출이 아닌 품목이 있어요', '금액이 영수증과 달라요', '이미 올라온 영수증이에요']

/**
 * 제출된 지출에서 할 수 있는 일 (서버가 준 can_* 기준).
 * 큰 버튼(승인·반려 / 보냈어요)은 화면 아래 막대에, 되돌리기는 내용 아래 글자 버튼으로.
 */
export function ExpenseActions({ orgId, expense }: { orgId: number; expense: ExpenseDetail }) {
  const action = useExpenseAction(orgId, expense.id)
  const { toast, confirm } = useFeedback()
  const [rejecting, setRejecting] = useState(false)
  const [reason, setReason] = useState('')
  const busy = action.isPending
  const payerAmount = `${expense.payer.name}님 · ${formatWon(expense.amount)}`

  async function run(next: ExpenseAction, done: string): Promise<boolean> {
    try {
      await action.mutateAsync(next)
      toast(done)
      return true
    } catch (error) {
      toast(errorMessage(error))
      return false
    }
  }

  async function approve() {
    const warnings = expense.budget_warnings
    const ok = await confirm(
      warnings.length > 0
        ? {
            title: '예산을 넘어요. 그래도 승인할까요?',
            message: warnings
              .map(
                (w) =>
                  `${w.category_name}: 예산 ${formatWon(w.budget)} 중 ${formatWon(w.spent)} 썼어요. 승인하면 ${formatWon(w.over_by)} 넘어요`,
              )
              .join('\n'),
            confirmLabel: '그래도 승인',
          }
        : { title: '승인할까요?', message: `${payerAmount}을 돌려줄 돈으로 잡아요`, confirmLabel: '승인하기' },
    )
    if (ok) await run({ type: 'approve' }, '승인했어요')
  }

  async function reject() {
    const text = reason.trim()
    if (!text) return
    if (await run({ type: 'reject', reason: text }, '반려했어요. 올린 사람에게 사유가 보여요')) {
      setRejecting(false)
      setReason('')
    }
  }

  async function reimburse() {
    const ok = await confirm({
      title: `${expense.payer.name}님에게 보냈나요?`,
      message: `${formatWon(expense.amount)}을 보냈으면 환급 완료로 표시해요. 송금은 각자 은행 앱으로 해주세요`,
      confirmLabel: '보냈어요',
    })
    if (ok) await run({ type: 'reimburse' }, '환급 완료로 표시했어요')
  }

  async function withdraw() {
    const ok = await confirm({
      title: '제출을 취소할까요?',
      message: '작성 중으로 돌아가요. 고친 뒤 다시 제출하면 돼요',
      confirmLabel: '제출 취소',
    })
    if (ok) await run({ type: 'withdraw' }, '제출을 취소했어요')
  }

  async function unapprove() {
    const ok = await confirm({ title: '승인을 취소할까요?', message: '승인 대기로 돌아가요', confirmLabel: '승인 취소', danger: true })
    if (ok) await run({ type: 'unapprove' }, '승인을 취소했어요')
  }

  async function unreimburse() {
    const ok = await confirm({
      title: '환급 완료를 취소할까요?',
      message: '아직 안 보낸 걸로 되돌려요',
      confirmLabel: '되돌리기',
      danger: true,
    })
    if (ok) await run({ type: 'unreimburse' }, '환급 완료를 취소했어요')
  }

  const cta = expense.can_review ? (
    <div className="btn-row">
      <button type="button" className="btn btn--secondary" onClick={() => setRejecting(true)} disabled={busy}>
        반려
      </button>
      <button type="button" className="btn btn--primary btn--grow" onClick={approve} disabled={busy}>
        {busy ? '처리 중…' : '승인하기'}
      </button>
    </div>
  ) : expense.can_reimburse ? (
    <button type="button" className="btn btn--primary btn--block" onClick={reimburse} disabled={busy}>
      <Icon name="send" size={20} />
      {busy ? '처리 중…' : `${expense.payer.name}님에게 보냈어요`}
    </button>
  ) : null

  const undo = [
    expense.can_withdraw && { label: '제출 취소', onClick: withdraw },
    expense.can_unapprove && { label: '승인 취소', onClick: unapprove },
    expense.can_unreimburse && { label: '환급 완료 취소', onClick: unreimburse },
  ].filter((item): item is { label: string; onClick: () => Promise<void> } => Boolean(item))

  return (
    <>
      {undo.length > 0 && (
        <div className="text-actions">
          {undo.map((item) => (
            <button key={item.label} type="button" className="btn btn--text" onClick={item.onClick} disabled={busy}>
              <Icon name="undo" size={18} />
              {item.label}
            </button>
          ))}
        </div>
      )}

      {cta && createPortal(<div className="cta-bar">{cta}</div>, document.body)}

      <BottomSheet
        open={rejecting}
        onClose={() => setRejecting(false)}
        title="반려 사유"
        description={`${payerAmount} · 올린 사람에게 보여요`}
      >
        <div className="sheet__body">
          <div className="reason-chips">
            {QUICK_REASONS.map((text) => (
              <button key={text} type="button" className="reason-chip press" onClick={() => setReason(text)}>
                {text}
              </button>
            ))}
          </div>
          <textarea
            className="textarea"
            aria-label="반려 사유"
            placeholder="무엇을 고치면 되는지 적어주세요"
            maxLength={500}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
        <div className="sheet__actions">
          <button type="button" className="btn btn--secondary" onClick={() => setRejecting(false)}>
            닫기
          </button>
          <button type="button" className="btn btn--danger" onClick={reject} disabled={busy || !reason.trim()}>
            반려하기
          </button>
        </div>
      </BottomSheet>
    </>
  )
}
