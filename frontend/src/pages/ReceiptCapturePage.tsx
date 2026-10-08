import { useEffect, useState, type ChangeEvent } from 'react'
import { useNavigate } from 'react-router'
import { errorMessage } from '../api/client'
import { useUploadReceipt } from '../api/expenses'
import { Page } from '../components/Page'
import { useOrgId } from '../hooks/useOrgId'

const MAX_BYTES = 15 * 1024 * 1024 // 서버 제한과 같게

type Picked = { file: File; url: string }

/** 영수증 촬영(또는 앨범에서 선택) → 업로드 → 인식 결과 확인·수정 화면으로 */
export function ReceiptCapturePage() {
  const orgId = useOrgId()
  const navigate = useNavigate()
  const upload = useUploadReceipt(orgId)
  const [picked, setPicked] = useState<Picked | null>(null)

  // 미리보기 URL은 바뀌거나 화면을 떠날 때 해제 (메모리 누수 방지)
  useEffect(() => {
    return () => {
      if (picked) URL.revokeObjectURL(picked.url)
    }
  }, [picked])

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = '' // 같은 사진을 다시 골라도 change가 일어나게
    upload.reset()
    setPicked(file ? { file, url: URL.createObjectURL(file) } : null)
  }

  function handleUpload() {
    if (!picked) return
    upload.mutate(picked.file, {
      // 뒤로 가기 하면 촬영 화면이 아니라 목록으로 가게 replace
      onSuccess: (expense) => navigate(`/orgs/${orgId}/expenses/${expense.id}`, { replace: true }),
    })
  }

  const tooLarge = picked !== null && picked.file.size > MAX_BYTES

  return (
    <Page title="영수증 촬영">
      <div className="capture-buttons">
        {/* 폰: 후면 카메라가 바로 열림 / PC: 파일 선택 */}
        <label className="button button--primary">
          {picked ? '다시 찍기' : '카메라로 찍기'}
          <input type="file" accept="image/*" capture="environment" hidden onChange={handleChange} />
        </label>
        <label className="button">
          앨범에서 고르기
          <input type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={handleChange} />
        </label>
      </div>
      <p className="muted">영수증 전체가 화면에 들어오게, 글자가 흔들리지 않게 찍어주세요. 인식은 몇 초 걸려요.</p>

      {picked && (
        <figure className="preview">
          <img src={picked.url} alt="선택한 영수증" />
          <figcaption className="muted">
            {picked.file.name} · {Math.round(picked.file.size / 1024).toLocaleString()}KB
          </figcaption>
        </figure>
      )}

      {tooLarge && <p className="error">사진 용량이 너무 커요. (최대 15MB)</p>}
      {upload.isError && <p className="error">{errorMessage(upload.error)}</p>}

      <button
        className="button button--primary"
        type="button"
        disabled={!picked || tooLarge || upload.isPending}
        onClick={handleUpload}
      >
        {upload.isPending ? '인식 중…' : '인식 시작'}
      </button>
    </Page>
  )
}
