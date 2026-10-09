import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { BottomSheet } from '../components/BottomSheet'
import { Icon } from '../components/Icon'
import { FeedbackContext, type ConfirmOptions } from './context'

type ToastState = { id: number; message: string; leaving: boolean }
type ConfirmState = { options: ConfirmOptions; resolve: (ok: boolean) => void; answered: boolean }

const TOAST_MS = 1800
const TOAST_OUT_MS = 280

/** 알림(토스트)·확인 시트를 앱 전체에 하나씩 둔다 (window.confirm 대신) */
export function FeedbackProvider({ children }: { children: ReactNode }) {
  const [toastState, setToastState] = useState<ToastState | null>(null)
  const [confirmState, setConfirmState] = useState<ConfirmState | null>(null)
  const timers = useRef<number[]>([])

  useEffect(() => () => timers.current.forEach((id) => window.clearTimeout(id)), [])

  const toast = useCallback((message: string) => {
    timers.current.forEach((id) => window.clearTimeout(id))
    const id = Date.now()
    setToastState({ id, message, leaving: false })
    timers.current = [
      window.setTimeout(() => setToastState((t) => (t?.id === id ? { ...t, leaving: true } : t)), TOAST_MS),
      window.setTimeout(() => setToastState((t) => (t?.id === id ? null : t)), TOAST_MS + TOAST_OUT_MS),
    ]
  }, [])

  // 지금 떠 있는 확인 창 (버튼 처리에서 바로 읽으려고 ref에도 둔다)
  const confirmRef = useRef<ConfirmState | null>(null)
  const showConfirm = useCallback((next: ConfirmState | null) => {
    confirmRef.current = next
    setConfirmState(next)
  }, [])

  const confirm = useCallback(
    (options: ConfirmOptions) =>
      new Promise<boolean>((resolve) => {
        confirmRef.current?.resolve(false) // 이전 창이 남아 있으면 취소로 끝냄
        showConfirm({ options, resolve, answered: false })
      }),
    [showConfirm],
  )

  const value = useMemo(() => ({ toast, confirm }), [toast, confirm])

  // 답하면 시트가 내려가고(answered), 다 내려간 뒤(onExited)에 내용을 지운다
  const answer = useCallback(
    (ok: boolean) => {
      const state = confirmRef.current
      if (!state || state.answered) return
      state.resolve(ok)
      showConfirm({ ...state, answered: true })
    },
    [showConfirm],
  )
  const cancel = useCallback(() => answer(false), [answer])

  const options = confirmState?.options
  return (
    <FeedbackContext.Provider value={value}>
      {children}
      {toastState &&
        createPortal(
          <div key={toastState.id} className="toast" role="status" data-leaving={toastState.leaving}>
            <span className="toast__icon">
              <Icon name="check" size={15} weight={3} />
            </span>
            {toastState.message}
          </div>,
          document.body,
        )}
      <BottomSheet
        open={confirmState !== null && !confirmState.answered}
        onClose={cancel}
        onExited={() => showConfirm(null)}
        title={options?.title ?? ''}
        description={options?.message}
      >
        <div className="sheet__actions">
          <button type="button" className="btn btn--secondary" onClick={cancel}>
            {options?.cancelLabel ?? '취소'}
          </button>
          <button
            type="button"
            className="btn btn--primary"
            style={options?.danger ? { background: 'var(--danger)' } : undefined}
            onClick={() => answer(true)}
          >
            {options?.confirmLabel ?? '확인'}
          </button>
        </div>
      </BottomSheet>
    </FeedbackContext.Provider>
  )
}
