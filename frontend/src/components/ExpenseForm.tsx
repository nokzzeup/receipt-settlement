import { useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router'
import { useCategories } from '../api/categories'
import { errorMessage } from '../api/client'
import { useDeleteExpense, useSaveExpense, useSubmitExpense } from '../api/expenses'
import { useMembers } from '../api/orgs'
import { ROLE_LABELS, type Category, type ExpenseDetail, type ExpenseItem, type ExpenseUpdate } from '../api/types'
import { useFeedback } from '../feedback/context'
import { categoryLook, chipStyle, tileStyle } from '../lib/categoryStyle'
import { formatWon, fromSeoulInput, parseInteger, toSeoulInput } from '../lib/format'
import { stagger } from '../lib/motion'
import { BottomSheet } from './BottomSheet'
import { Icon } from './Icon'
import { NumberInput } from './NumberInput'
import { OcrText } from './OcrText'
import { ReceiptThumb } from './ReceiptImage'

/** 입력 중인 품목 (입력칸 값이라 전부 문자열) */
type ItemDraft = {
  key: string
  name: string
  quantity: string
  unitPrice: string
  amount: string
  categoryId: string // '' = 미분류
  /** 서버가 자동으로 고른 계정과목이고 아직 안 바꿈 → '자동' 표시 */
  auto: boolean
}

type FormState = {
  storeName: string
  paidAt: string // datetime-local 값 (한국시간)
  totalAmount: string
  payerId: string
  items: ItemDraft[]
}

let keySeq = 0
const newKey = () => `item-${++keySeq}`

const toDraft = (item: ExpenseItem): ItemDraft => ({
  key: newKey(),
  name: item.name,
  quantity: String(item.quantity),
  unitPrice: item.unit_price?.toString() ?? '',
  amount: String(item.amount),
  categoryId: item.category_id?.toString() ?? '',
  auto: item.category_source === 'AUTO' && item.category_id !== null,
})

const emptyDraft = (): ItemDraft => ({
  key: newKey(),
  name: '',
  quantity: '1',
  unitPrice: '',
  amount: '',
  categoryId: '',
  auto: false,
})

function initialState(expense: ExpenseDetail): FormState {
  return {
    storeName: expense.receipt.store_name ?? '',
    paidAt: toSeoulInput(expense.receipt.paid_at),
    totalAmount: expense.receipt.total_amount?.toString() ?? '',
    payerId: String(expense.payer.membership_id),
    items: expense.items.map(toDraft),
  }
}

const isBlank = (item: ItemDraft) => !item.name.trim() && !item.amount.trim() && !item.unitPrice.trim()

/** 입력값 → API 요청 본문. 잘못된 값이 있으면 사람이 읽을 메시지 */
function buildBody(state: FormState): { body: ExpenseUpdate } | { error: string } {
  const total = parseInteger(state.totalAmount)
  if (total === undefined || (total !== null && total < 0)) return { error: '영수증 합계는 0 이상의 정수(원)로 입력하세요.' }

  const items: ExpenseUpdate['items'] = []
  for (const [index, item] of state.items.entries()) {
    const n = index + 1
    if (isBlank(item)) continue // 빈 줄은 무시
    if (!item.name.trim()) return { error: `${n}번째 품목의 이름을 입력하세요.` }
    const quantity = parseInteger(item.quantity)
    if (quantity == null || quantity < 1) return { error: `${n}번째 품목의 수량은 1 이상의 정수여야 합니다.` }
    const unitPrice = parseInteger(item.unitPrice)
    if (unitPrice === undefined) return { error: `${n}번째 품목의 단가는 정수(원)로 입력하세요.` }
    const amount = parseInteger(item.amount)
    if (amount == null) return { error: `${n}번째 품목의 금액을 정수(원)로 입력하세요.` }
    items.push({
      name: item.name.trim(),
      quantity,
      unit_price: unitPrice,
      amount,
      category_id: item.categoryId ? Number(item.categoryId) : null,
    })
  }

  return {
    body: {
      store_name: state.storeName.trim() || null,
      paid_at: fromSeoulInput(state.paidAt),
      total_amount: total,
      payer_membership_id: Number(state.payerId),
      items,
    },
  }
}

type Props = {
  orgId: number
  expense: ExpenseDetail
  /** 제출까지 끝나면 (완료 화면은 페이지가 띄움 — 제출하면 이 폼은 읽기 전용 화면으로 바뀌어 사라지므로) */
  onSubmitted: (expense: ExpenseDetail) => void
}

/** 인식 결과 확인·수정 (작성 중 지출). 임시 저장 / 제출 / 삭제 */
export function ExpenseForm({ orgId, expense, onSubmitted }: Props) {
  const navigate = useNavigate()
  const { toast, confirm } = useFeedback()
  const categories = useCategories(orgId)
  const members = useMembers(orgId)
  const save = useSaveExpense(orgId, expense.id)
  const submit = useSubmitExpense(orgId, expense.id)
  const remove = useDeleteExpense(orgId, expense.id)

  const [state, setState] = useState<FormState>(() => initialState(expense))
  const [formError, setFormError] = useState<string | null>(null)
  // 계정과목 고르기 시트: 어느 품목인지 + 열림 (닫히는 동안에도 제목이 보이게 key는 남겨둠)
  const [sheet, setSheet] = useState<{ key: string; open: boolean } | null>(null)
  // 방금 계정을 고른 품목 → 칩이 톡 튀어나옴
  const [popped, setPopped] = useState<string | null>(null)
  // 제출 막힘 → 해당 품목이 좌우로 흔들림 (다시 막히면 이름을 바꿔 처음부터)
  const [shake, setShake] = useState<{ keys: string[]; flip: boolean }>({ keys: [], flip: false })

  const busy = save.isPending || submit.isPending || remove.isPending
  const serverError = save.error ?? submit.error ?? remove.error

  const total = parseInteger(state.totalAmount)
  const claimed = state.items.reduce((sum, item) => sum + (parseInteger(item.amount) ?? 0), 0)
  const uncategorized = state.items.filter((item) => !isBlank(item) && !item.categoryId)
  const categoryById = (id: string): Category | undefined => categories.data?.find((c) => String(c.id) === id)

  function setField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setState((prev) => ({ ...prev, [key]: value }))
  }

  function updateItem(key: string, patch: Partial<ItemDraft>) {
    setState((prev) => ({
      ...prev,
      items: prev.items.map((item) => {
        if (item.key !== key) return item
        const next = { ...item, ...patch }
        // 수량·단가를 바꾸면 금액 자동 계산 (금액을 직접 고치는 것도 가능 — 할인 등)
        if ('quantity' in patch || 'unitPrice' in patch) {
          const quantity = parseInteger(next.quantity)
          const unitPrice = parseInteger(next.unitPrice)
          if (quantity != null && unitPrice != null) next.amount = String(quantity * unitPrice)
        }
        // 이름이나 계정과목을 바꾸면 더 이상 '자동'이 아님 (서버도 같은 기준)
        if ('name' in patch || 'categoryId' in patch) next.auto = false
        return next
      }),
    }))
  }

  function chooseCategory(categoryId: string) {
    if (!sheet) return
    updateItem(sheet.key, { categoryId })
    setPopped(sheet.key)
    setSheet({ ...sheet, open: false })
    setFormError(null)
  }

  function flipSign(item: ItemDraft) {
    const amount = parseInteger(item.amount)
    if (amount) updateItem(item.key, { amount: String(-amount) })
  }

  function resetMessages() {
    setFormError(null)
    save.reset()
    submit.reset()
    remove.reset()
  }

  /** 입력값 검사 → 요청 본문. 잘못됐으면 메시지를 띄우고 null */
  function validated(): ExpenseUpdate | null {
    resetMessages()
    const built = buildBody(state)
    if ('error' in built) {
      setFormError(built.error)
      return null
    }
    return built.body
  }

  /** 저장 성공하면 true (실패 메시지는 save.error로 표시) */
  async function saveDraft(body: ExpenseUpdate): Promise<boolean> {
    try {
      await save.mutateAsync(body)
      return true
    } catch {
      return false
    }
  }

  async function handleSave() {
    const body = validated()
    if (body && (await saveDraft(body))) toast('저장했어요. 나중에 이어서 고칠 수 있어요')
  }

  async function handleSubmit() {
    const body = validated()
    if (!body) return
    if (uncategorized.length > 0) {
      setFormError(`계정과목을 고르지 않은 품목이 ${uncategorized.length}개 있어요`)
      setShake((s) => ({ keys: uncategorized.map((item) => item.key), flip: !s.flip }))
      return
    }
    const ok = await confirm({
      title: '제출할까요?',
      message: '제출하면 승인 대기 상태가 되고 더 이상 고칠 수 없어요.',
      confirmLabel: '제출하기',
    })
    if (!ok) return
    // 화면에서 고친 내용을 먼저 저장하고, 저장된 내용 기준으로 서버가 제출 조건을 검사
    if (!(await saveDraft(body))) return
    try {
      onSubmitted(await submit.mutateAsync())
    } catch {
      // 메시지는 submit.error로 표시
    }
  }

  async function handleDelete() {
    const ok = await confirm({
      title: '이 지출을 삭제할까요?',
      message: '영수증 사진도 같이 지워지고 되돌릴 수 없어요.',
      confirmLabel: '삭제',
      danger: true,
    })
    if (!ok) return
    resetMessages()
    remove.mutate(undefined, {
      onSuccess: () => {
        toast('지출을 삭제했어요')
        navigate(`/orgs/${orgId}/expenses`, { replace: true })
      },
    })
  }

  const sheetItem = sheet ? state.items.find((item) => item.key === sheet.key) : undefined
  const message = formError ?? (serverError ? errorMessage(serverError) : null)

  return (
    <>
      {expense.receipt.ocr_failed ? (
        <p className="banner banner--warn anim-rise">
          <Icon name="alert" size={20} />
          자동 인식에 실패했어요. 사진을 보면서 직접 입력해 주세요
        </p>
      ) : (
        <p className="banner anim-rise">
          <Icon name="sparkle" size={20} />
          자동으로 채웠어요. 사진과 비교해서 틀린 곳만 고쳐주세요
        </p>
      )}

      <section className="card receipt-fields anim-rise" style={stagger(1)} aria-label="영수증 정보">
        <ReceiptThumb orgId={orgId} expenseId={expense.id} />
        <div className="receipt-fields__inputs">
          <label className="field">
            <span className="field__label">가게</span>
            <input
              className="input-line"
              value={state.storeName}
              onChange={(e) => setField('storeName', e.target.value)}
              placeholder="가게 이름"
              maxLength={200}
            />
          </label>
          <label className="field">
            <span className="field__label">결제일시</span>
            <input
              className="input-line"
              type="datetime-local"
              value={state.paidAt}
              onChange={(e) => setField('paidAt', e.target.value)}
            />
          </label>
        </div>
      </section>

      <section className="card anim-rise" style={stagger(2)} aria-label="합계와 결제한 사람">
        <label className="field">
          <span className="field__label">영수증 합계</span>
          <span style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
            <NumberInput
              className="input-line input-line--amount"
              value={state.totalAmount}
              onValueChange={(value) => setField('totalAmount', value)}
              placeholder="0"
              aria-label="영수증 합계(원)"
            />
            <span style={{ fontSize: 20, fontWeight: 700 }}>원</span>
          </span>
        </label>
        <TotalCheck total={total} claimed={claimed} />
        <label className="payer-row">
          <span>결제한 사람 (돌려받을 사람)</span>
          <select className="select" value={state.payerId} onChange={(e) => setField('payerId', e.target.value)}>
            {members.data ? (
              members.data.map((m) => (
                <option key={m.membership_id} value={m.membership_id}>
                  {m.name} ({ROLE_LABELS[m.role]})
                </option>
              ))
            ) : (
              <option value={state.payerId}>{expense.payer.name}</option>
            )}
          </select>
        </label>
      </section>

      <section className="card card--list anim-rise" style={{ ...stagger(3), paddingInline: 16 }} aria-label="품목">
        <div className="card__head" style={{ padding: '0 4px' }}>
          <h2 className="card__title">품목 {state.items.length}개</h2>
          <span className="card__sub">계정은 품목마다 달라도 돼요</span>
        </div>
        <div style={{ marginTop: 4 }}>
          {state.items.length === 0 && (
            <p className="caption" style={{ padding: '14px 4px' }}>
              품목이 없어요. 아래 버튼으로 추가하세요
            </p>
          )}
          {state.items.map((item, index) => {
            const n = index + 1
            const category = categoryById(item.categoryId)
            const look = categoryLook(category)
            const shaking = shake.keys.includes(item.key)
            const shakeClass = shaking ? (shake.flip ? ' anim-shake-2' : ' anim-shake') : ''
            return (
              <div key={item.key} className={`item-card${shakeClass}`}>
                <div className="item-card__head">
                  <input
                    className="input-line"
                    aria-label={`${n}번째 품목 이름`}
                    placeholder="품목 이름"
                    value={item.name}
                    onChange={(e) => updateItem(item.key, { name: e.target.value })}
                    maxLength={200}
                  />
                  <button
                    type="button"
                    className="icon-btn icon-btn--sm"
                    aria-label={`${n}번째 품목 삭제`}
                    onClick={() => setField('items', state.items.filter((it) => it.key !== item.key))}
                  >
                    <Icon name="close" size={18} />
                  </button>
                </div>
                <div className="item-card__numbers">
                  <label className="field">
                    <span className="field__label">수량</span>
                    <NumberInput
                      className="input-box"
                      value={item.quantity}
                      onValueChange={(value) => updateItem(item.key, { quantity: value })}
                    />
                  </label>
                  <label className="field">
                    <span className="field__label">단가</span>
                    <NumberInput
                      className="input-box"
                      value={item.unitPrice}
                      onValueChange={(value) => updateItem(item.key, { unitPrice: value })}
                    />
                  </label>
                  <label className="field">
                    <span className="field__label">금액</span>
                    <NumberInput
                      className="input-box"
                      value={item.amount}
                      onValueChange={(value) => updateItem(item.key, { amount: value })}
                      style={{ fontWeight: 700 }}
                    />
                  </label>
                  {/* 숫자 키패드에는 '-'가 없는 폰이 있어서, 할인 줄은 이 버튼으로 음수로 바꾼다 */}
                  <button
                    type="button"
                    className="icon-btn icon-btn--sm"
                    aria-label={`${n}번째 품목 금액 부호 바꾸기 (할인)`}
                    title="할인이면 음수로"
                    onClick={() => flipSign(item)}
                    style={{ height: 40, fontSize: 17, fontWeight: 700 }}
                  >
                    ±
                  </button>
                </div>
                <div>
                  {category ? (
                    <button
                      key={item.categoryId}
                      type="button"
                      className={popped === item.key ? 'cat-chip press anim-pop' : 'cat-chip press'}
                      style={chipStyle(look)}
                      onClick={() => setSheet({ key: item.key, open: true })}
                      aria-label={`${n}번째 품목 계정과목: ${category.name} (바꾸기)`}
                    >
                      <span className="cat-chip__icon" style={{ color: look.fg }}>
                        <Icon name={look.icon} size={16} />
                      </span>
                      {category.name}
                      {item.auto && <span className="auto-badge">자동</span>}
                      <Icon name="chevronDown" size={16} />
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="cat-chip cat-chip--empty press"
                      onClick={() => setSheet({ key: item.key, open: true })}
                      aria-label={`${n}번째 품목 계정과목 고르기`}
                    >
                      <Icon name="plus" size={18} />
                      계정 고르기
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
        <button type="button" className="add-row press" onClick={() => setField('items', [...state.items, emptyDraft()])}>
          <Icon name="plus" size={18} />
          품목 추가
        </button>
        <div className="sum-line" style={{ marginTop: 8 }}>
          <span>청구 금액 (품목 합계)</span>
          <span className="amount">{formatWon(claimed)}</span>
        </div>
      </section>

      <OcrText lines={expense.receipt.ocr_text} />

      <button type="button" className="btn btn--danger-text" onClick={handleDelete} disabled={busy}>
        이 지출 삭제
      </button>

      <BottomSheet
        open={sheet?.open ?? false}
        onClose={() => sheet && setSheet({ ...sheet, open: false })}
        onExited={() => setSheet(null)}
        title="계정 고르기"
        description={
          sheetItem
            ? `${sheetItem.name || '이름 없는 품목'} · ${formatWon(parseInteger(sheetItem.amount) ?? 0)}`
            : undefined
        }
      >
        <div className="chip-grid sheet__body">
          {categories.data?.map((c, i) => {
            const look = categoryLook(c)
            return (
              <button
                key={c.id}
                type="button"
                className="chip-option press anim-rise"
                style={stagger(i)}
                aria-pressed={sheetItem?.categoryId === String(c.id)}
                onClick={() => chooseCategory(String(c.id))}
              >
                <span className="tile tile--sm tile--round" style={tileStyle(look)}>
                  <Icon name={look.icon} size={17} />
                </span>
                {c.name}
              </button>
            )
          })}
          {sheetItem?.categoryId && (
            <button type="button" className="chip-option press" onClick={() => chooseCategory('')}>
              <span className="tile tile--sm tile--round">
                <Icon name="close" size={16} />
              </span>
              미분류로
            </button>
          )}
        </div>
        {categories.data?.length === 0 && <p className="caption">계정과목이 없어요. 총무가 설정에서 추가할 수 있어요</p>}
      </BottomSheet>

      {createPortal(
        <div className="cta-bar">
          {message && (
            <p key={message} className="message message--error anim-rise" role="alert">
              <Icon name="alert" size={18} />
              {message}
            </p>
          )}
          <div className="btn-row">
            <button type="button" className="btn btn--secondary" onClick={handleSave} disabled={busy}>
              {save.isPending && !submit.isPending ? '저장 중…' : '임시 저장'}
            </button>
            <button type="button" className="btn btn--primary btn--grow" onClick={handleSubmit} disabled={busy}>
              {submit.isPending ? '제출 중…' : '제출하기'}
            </button>
          </div>
        </div>,
        document.body,
      )}
    </>
  )
}

/** 영수증 합계 vs 품목 합계 (개인적으로 산 품목을 지우면 그만큼 청구에서 빠짐) */
function TotalCheck({ total, claimed }: { total: number | null | undefined; claimed: number }) {
  if (total == null) return <p className="message message--muted" style={{ marginTop: 8 }}>영수증 합계를 넣으면 품목 합계와 비교해 드려요</p>
  if (claimed === total) {
    return (
      <p className="message message--ok" style={{ marginTop: 8 }}>
        <Icon name="checkCircle" size={18} />
        품목 합계와 같아요
      </p>
    )
  }
  if (claimed < total) {
    return (
      <p className="message message--muted" style={{ marginTop: 8 }}>
        <Icon name="info" size={18} />
        영수증 중 {formatWon(total - claimed)}은 청구에서 빠져요
      </p>
    )
  }
  return (
    <p className="message message--error" style={{ marginTop: 8 }}>
      <Icon name="alert" size={18} />
      품목 합계가 영수증보다 {formatWon(claimed - total)} 많아요
    </p>
  )
}
