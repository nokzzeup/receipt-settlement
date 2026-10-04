import { useEffect, useState, type ChangeEvent } from 'react'
import { Page } from '../components/Page'

type Picked = { file: File; url: string }

export function ReceiptCapturePage() {
  const [picked, setPicked] = useState<Picked | null>(null)

  // 미리보기 URL은 바뀌거나 화면을 떠날 때 해제 (메모리 누수 방지)
  useEffect(() => {
    return () => {
      if (picked) URL.revokeObjectURL(picked.url)
    }
  }, [picked])

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    setPicked(file ? { file, url: URL.createObjectURL(file) } : null)
  }

  return (
    <Page title="영수증 촬영" todo="2단계: 업로드 API → Mock OCR → 인식 결과 확인 화면으로 이동">
      {/* 폰: 후면 카메라가 바로 열림 / PC: 파일 선택 */}
      <label className="button capture">
        {picked ? '다시 찍기' : '영수증 촬영 / 사진 선택'}
        <input type="file" accept="image/*" capture="environment" hidden onChange={handleChange} />
      </label>

      {picked && (
        <figure className="preview">
          <img src={picked.url} alt="선택한 영수증" />
          <figcaption className="muted">
            {picked.file.name} · {Math.round(picked.file.size / 1024)}KB
          </figcaption>
        </figure>
      )}

      <button className="button button--primary" type="button" disabled={!picked}>
        인식 시작
      </button>
    </Page>
  )
}
