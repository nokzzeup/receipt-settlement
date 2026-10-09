import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import { useNavigate } from 'react-router'
import { errorMessage } from '../api/client'
import { useUploadReceipt } from '../api/expenses'
import { Icon } from '../components/Icon'
import { TopBar } from '../components/TopBar'
import { useOrgId } from '../hooks/useOrgId'
import { stagger } from '../lib/motion'

const MAX_BYTES = 15 * 1024 * 1024 // 서버 제한과 같게

type Picked = { file: File; url: string }

const TITLES = {
  guide: ['영수증을 찍어주세요', '글자를 읽어서 가게·날짜·품목을 채워드려요'],
  preview: ['이 사진으로 읽을게요', '글자가 흐리면 다시 찍는 게 더 정확해요'],
  scanning: ['영수증을 읽고 있어요', '보통 3~5초 걸려요'],
} as const

/**
 * 영수증 찍기 → 미리보기 → 인식(스캔 줄이 오르내림) → 확인·수정 화면으로.
 * 폰: '카메라로 찍기'가 후면 카메라를 바로 연다 / PC: 파일 선택
 */
export function ReceiptCapturePage() {
  const orgId = useOrgId()
  const navigate = useNavigate()
  const upload = useUploadReceipt(orgId)
  const [picked, setPicked] = useState<Picked | null>(null)
  const cameraInput = useRef<HTMLInputElement>(null)
  const albumInput = useRef<HTMLInputElement>(null)

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
    if (file) setPicked({ file, url: URL.createObjectURL(file) })
  }

  function handleUpload() {
    if (!picked) return
    upload.mutate(picked.file, {
      // 뒤로 가기 하면 촬영 화면이 아니라 이전 화면으로 가게 replace
      onSuccess: (expense) => navigate(`/orgs/${orgId}/expenses/${expense.id}`, { replace: true }),
    })
  }

  function retake() {
    upload.reset()
    setPicked(null)
  }

  const phase = upload.isPending ? 'scanning' : picked ? 'preview' : 'guide'
  const tooLarge = picked !== null && picked.file.size > MAX_BYTES
  const [title, subtitle] = TITLES[phase]

  return (
    <>
      <TopBar title="영수증 찍기" back={`/orgs/${orgId}`} close />
      <div className="screen" style={{ minHeight: 'calc(100dvh - 56px)' }}>
        {/* 단계가 바뀔 때마다 제목이 새로 떠오르게 */}
        <div key={phase} className="large-title anim-rise" style={{ paddingTop: 0 }}>
          <h1 style={{ fontSize: 24 }}>{title}</h1>
          <p>{subtitle}</p>
        </div>

        <div className={phase === 'guide' ? 'viewfinder viewfinder--guide' : 'viewfinder'}>
          <span className="viewfinder__corner viewfinder__corner--tl" aria-hidden="true" />
          <span className="viewfinder__corner viewfinder__corner--tr" aria-hidden="true" />
          <span className="viewfinder__corner viewfinder__corner--bl" aria-hidden="true" />
          <span className="viewfinder__corner viewfinder__corner--br" aria-hidden="true" />
          {picked ? (
            <figure key={picked.url} className="viewfinder__photo">
              <img src={picked.url} alt="고른 영수증 사진" />
              {phase === 'scanning' && <span className="scanline" aria-hidden="true" />}
            </figure>
          ) : (
            <div className="viewfinder__ghost anim-fade" aria-hidden="true">
              <Icon name="receipt" size={30} />
              영수증 전체가
              <br />이 안에 들어오게
            </div>
          )}
        </div>

        {phase === 'guide' && (
          <ul className="tips">
            {['영수증 전체가 화면에 들어오게', '그림자 없이 밝은 곳에서', '구겨진 곳은 펴서 찍어주세요'].map((tip, i) => (
              <li key={tip} className="anim-rise" style={stagger(i + 1)}>
                <Icon name="checkCircle" size={20} />
                {tip}
              </li>
            ))}
          </ul>
        )}
        {phase === 'preview' && picked && (
          <p className="caption anim-fade" style={{ padding: '0 4px' }}>
            {picked.file.name} · {Math.round(picked.file.size / 1024).toLocaleString()}KB
          </p>
        )}
        {phase === 'scanning' && (
          <div className="card anim-fade" aria-hidden="true" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <span className="skeleton" style={{ height: 14, width: '42%' }} />
            <span className="skeleton" style={{ height: 14, width: '70%' }} />
            <span className="skeleton" style={{ height: 14, width: '56%' }} />
          </div>
        )}

        {tooLarge && <p className="message message--error">사진 용량이 너무 커요. (최대 15MB)</p>}
        {upload.isError && (
          <p className="message message--error anim-rise" role="alert">
            <Icon name="alert" size={18} />
            {errorMessage(upload.error)}
          </p>
        )}

        <div className="bottom-actions">
          {phase === 'guide' && (
            <>
              <button type="button" className="btn btn--primary btn--block anim-rise" style={stagger(2)} onClick={() => cameraInput.current?.click()}>
                <Icon name="camera" size={22} />
                카메라로 찍기
              </button>
              <button type="button" className="btn btn--text btn--block" onClick={() => albumInput.current?.click()}>
                <Icon name="image" size={20} />
                앨범에서 고르기
              </button>
            </>
          )}
          {phase === 'preview' && (
            <div className="btn-row anim-rise">
              <button type="button" className="btn btn--secondary" onClick={retake}>
                다시 고르기
              </button>
              <button type="button" className="btn btn--primary btn--grow" onClick={handleUpload} disabled={tooLarge}>
                인식 시작
              </button>
            </div>
          )}
          {phase === 'scanning' && (
            <button type="button" className="btn btn--primary btn--block" disabled>
              <Icon name="loader" size={20} weight={2.4} className="spinner" />
              읽는 중…
            </button>
          )}
        </div>

        {/* 폰: 후면 카메라가 바로 열림 / PC: 파일 선택. 버튼이 대신 눌러줌 */}
        <input ref={cameraInput} type="file" accept="image/*" capture="environment" hidden onChange={handleChange} />
        <input ref={albumInput} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={handleChange} />
      </div>
    </>
  )
}
