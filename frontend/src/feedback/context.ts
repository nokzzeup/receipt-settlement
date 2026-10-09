import { createContext, useContext } from 'react'

export type ConfirmOptions = {
  title: string
  message?: string
  confirmLabel?: string
  cancelLabel?: string
  /** 삭제처럼 되돌릴 수 없는 일이면 빨간 버튼 */
  danger?: boolean
}

export type Feedback = {
  /** 아래쪽에 잠깐 떴다 사라지는 알림 */
  toast: (message: string) => void
  /** 확인 시트를 띄우고 누른 결과 (확인 = true) */
  confirm: (options: ConfirmOptions) => Promise<boolean>
}

export const FeedbackContext = createContext<Feedback | null>(null)

/** 알림·확인 창. 화면 어디서나 (FeedbackProvider 안) */
export function useFeedback(): Feedback {
  const value = useContext(FeedbackContext)
  if (!value) throw new Error('useFeedback은 FeedbackProvider 안에서만 쓸 수 있어요')
  return value
}
