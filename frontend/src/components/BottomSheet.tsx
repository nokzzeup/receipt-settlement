import { useEffect, useId, useRef, useState, type AnimationEvent, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

type Props = {
  open: boolean
  /** 바깥(어두운 곳)·Esc·닫기 버튼 */
  onClose: () => void
  /** 닫히는 움직임까지 끝난 뒤 (내용을 이때 지우면 닫히는 동안에도 내용이 보임) */
  onExited?: () => void
  title: string
  description?: ReactNode
  children?: ReactNode
}

/**
 * 아래에서 올라오는 시트. 열릴 때 올라오고, 닫힐 때 내려간 뒤에 사라진다.
 * 열려 있는 동안 뒤 화면 스크롤을 막고, 닫히면 원래 누르던 버튼으로 포커스를 돌려준다.
 */
export function BottomSheet({ open, onClose, onExited, title, description, children }: Props) {
  const titleId = useId()
  const sheetRef = useRef<HTMLDivElement>(null)
  const [mounted, setMounted] = useState(open)
  const [prevOpen, setPrevOpen] = useState(open)
  // open이 바뀌면 렌더 중에 바로 반영 (닫힐 때는 움직임이 끝날 때까지 남겨둠)
  if (open !== prevOpen) {
    setPrevOpen(open)
    if (open) setMounted(true)
  }
  const closing = mounted && !open

  useEffect(() => {
    if (!open) return
    const opener = document.activeElement as HTMLElement | null
    sheetRef.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      opener?.focus?.()
    }
  }, [open, onClose])

  useEffect(() => {
    if (!mounted) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [mounted])

  function handleAnimationEnd(event: AnimationEvent<HTMLDivElement>) {
    if (closing && event.target === event.currentTarget) {
      setMounted(false)
      onExited?.()
    }
  }

  if (!mounted) return null
  return createPortal(
    <>
      <button
        type="button"
        className="sheet-backdrop"
        data-closing={closing}
        aria-label="닫기"
        tabIndex={-1}
        onClick={onClose}
      />
      <div
        ref={sheetRef}
        className="sheet"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        data-closing={closing}
        onAnimationEnd={handleAnimationEnd}
      >
        <div className="sheet__handle" aria-hidden="true" />
        <h2 id={titleId} className="sheet__title">
          {title}
        </h2>
        {description && <p className="sheet__desc">{description}</p>}
        {children}
      </div>
    </>,
    document.body,
  )
}
