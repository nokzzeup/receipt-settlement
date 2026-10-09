import { useId, useState } from 'react'
import { Icon } from './Icon'

/** 인식된 원문 (카드번호는 서버에서 가림). 누르면 높이가 부드럽게 늘어나며 펼쳐짐 */
export function OcrText({ lines }: { lines: string[] }) {
  const [open, setOpen] = useState(false)
  const id = useId()
  if (lines.length === 0) return null
  return (
    <section className="card" style={{ padding: '4px 16px' }} aria-label="인식된 원문">
      <button
        type="button"
        className="collapse-toggle"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
      >
        인식된 원문 보기 ({lines.length}줄)
        <Icon name="chevronDown" size={18} />
      </button>
      <div id={id} className="collapsible" data-open={open}>
        <div>
          <pre className="ocr-lines">{lines.join('\n')}</pre>
        </div>
      </div>
    </section>
  )
}
