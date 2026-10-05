import { useState } from 'react'
import { useNavigate } from 'react-router'
import { useCategories } from '../api/categories'
import { errorMessage } from '../api/client'
import { useDeleteExpense, useSaveExpense, useSubmitExpense } from '../api/expenses'
import { useMembers } from '../api/orgs'
import { ROLE_LABELS, type ExpenseDetail, type ExpenseItem, type ExpenseUpdate } from '../api/types'
import { formatWon, fromSeoulInput, parseInteger, toSeoulInput } from '../lib/format'

/** 입력 중인 품목 (입력칸 값이라 전부 문자열) */
type ItemDraft = {
  key: string
  name: string
  quantity: string
  unitPrice: string
  amount: string
  categoryId: string // '' = 미분류
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
})

const emptyDraft = (): ItemDraft => ({
  key: newKey(),
  name: '',
  quantity: '1',
  unitPrice: '',
  amount: '',
  categoryId: '',
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

/** 입력값 → API 요청 본문. 잘못된 값이 있으면 사람이 읽을 메시지 */
function buildBody(state: FormState): { body: ExpenseUpdate } | { error: string } {
  const total = parseInteger(state.totalAmount)
  if (total === undefined || (total !== null && total < 0)) return { error: '영수증 합계는 0 이상의 정수(원)로 입력하세요.' }

  const items: ExpenseUpdate['items'] = []
  for (const [index, item] of state.items.entries()) {
    const n = index + 1
    if (!item.name.trim() && !item.amount.trim() && !item.unitPrice.trim()) continue // 빈 줄은 무시
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

type Props = { orgId: number; expense: ExpenseDetail }

/** 인식 결과 확인·수정 (작성 중 지출). 임시 저장 / 제출 / 삭제 */
export function ExpenseForm({ orgId, expense }: Props) {
  const navigate = useNavigate()
  const categories = useCategories(orgId)
  const members = useMembers(orgId)
  const save = useSaveExpense(orgId, expense.id)
  const submit = useSubmitExpense(orgId, expense.id)
  const remove = useDeleteExpense(orgId, expense.id)

  const [state, setState] = useState<FormState>(() => initialState(expense))
  const [formError, setFormError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const busy = save.isPending || submit.isPending || remove.isPending
  const serverError = save.error ?? submit.error ?? remove.error

  const total = parseInteger(state.totalAmount)
  const claimed = state.items.reduce((sum, item) => sum + (parseInteger(item.amount) ?? 0), 0)
  const uncategorized = state.items.filter((item) => item.name.trim() && !item.categoryId).length

  function setField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setSaved(false)
    setState((prev) => ({ ...prev, [key]: value }))
  }

  function updateItem(key: string, patch: Partial<ItemDraft>) {
    setSaved(false)
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
        return next
      }),
    }))
  }

  function removeItem(key: string) {
    setField(
      'items',
      state.items.filter((item) => item.key !== key),
    )
  }

  function resetMessages() {
    setFormError(null)
    setSaved(false)
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
    if (body && (await saveDraft(body))) setSaved(true)
  }

  async function handleSubmit() {
    const body = validated()
    if (!body) return
    if (!window.confirm('제출하면 승인 대기 상태가 되고 더 이상 고칠 수 없어요. 제출할까요?')) return
    // 화면에서 고친 내용을 먼저 저장하고, 저장된 내용 기준으로 서버가 제출 조건을 검사
    if (await saveDraft(body)) submit.mutate()
  }

  function flipSign(item: ItemDraft) {
    const amount = parseInteger(item.amount)
    if (amount) updateItem(item.key, { amount: String(-amount) })
  }

  function handleDelete() {
    if (!window.confirm('이 지출과 영수증 사진을 삭제할까요?')) return
    resetMessages()
    remove.mutate(undefined, { onSuccess: () => navigate(`/orgs/${orgId}/expenses`, { replace: true }) })
  }

  return (
    <div className="stack expense-form">
      {expense.receipt.ocr_failed ? (
        <p className="notice notice--warn">자동 인식에 실패했어요. 사진을 보면서 직접 입력해 주세요.</p>
      ) : (
        <p className="notice">사진과 비교해서 틀린 곳을 고쳐주세요. 개인적으로 산 품목은 지우면 청구 금액에서 빠져요.</p>
      )}

      <section className="card stack">
        <h2 className="card__title">영수증</h2>
        <label className="field">
          <span className="field__label">가게명</span>
          <input
            className="input"
            value={state.storeName}
            onChange={(e) => setField('storeName', e.target.value)}
            maxLength={200}
          />
        </label>
        <label className="field">
          <span className="field__label">결제일시</span>
          <input
            className="input"
            type="datetime-local"
            value={state.paidAt}
            onChange={(e) => setField('paidAt', e.target.value)}
          />
        </label>
        <label className="field">
          <span className="field__label">영수증 합계(원)</span>
          <input
            className="input"
            inputMode="numeric"
            value={state.totalAmount}
            onChange={(e) => setField('totalAmount', e.target.value)}
          />
        </label>
        <label className="field">
          <span className="field__label">결제자 (환급받을 사람)</span>
          <select className="select" value={state.payerId} onChange={(e) => setField('payerId', e.target.value)}>
            {members.data
              ? members.data.map((m) => (
                  <option key={m.membership_id} value={m.membership_id}>
                    {m.name} ({ROLE_LABELS[m.role]})
                  </option>
                ))
              : <option value={state.payerId}>{expense.payer.name}</option>}
          </select>
        </label>
      </section>

      <section className="card stack">
        <h2 className="card__title">품목 {state.items.length}개</h2>
        {state.items.length === 0 && <p className="muted">품목이 없어요. 아래 버튼으로 추가하세요.</p>}
        {state.items.map((item, index) => (
          <div key={item.key} className="item-card">
            <div className="row">
              <input
                className="input"
                aria-label={`${index + 1}번째 품목 이름`}
                placeholder="품목 이름"
                value={item.name}
                onChange={(e) => updateItem(item.key, { name: e.target.value })}
                maxLength={200}
              />
              <button
                type="button"
                className="icon-button"
                aria-label={`${index + 1}번째 품목 삭제`}
                onClick={() => removeItem(item.key)}
              >
                ✕
              </button>
            </div>
            <select
              className={item.categoryId ? 'select' : 'select select--empty'}
              aria-label={`${index + 1}번째 품목 계정과목`}
              value={item.categoryId}
              onChange={(e) => updateItem(item.key, { categoryId: e.target.value })}
            >
              <option value="">계정과목 선택 (미분류)</option>
              {categories.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            <div className="item-card__numbers">
              <label className="field">
                <span className="field__label">수량</span>
                <input
                  className="input"
                  inputMode="numeric"
                  value={item.quantity}
                  onChange={(e) => updateItem(item.key, { quantity: e.target.value })}
                />
              </label>
              <label className="field">
                <span className="field__label">단가</span>
                <input
                  className="input"
                  inputMode="numeric"
                  value={item.unitPrice}
                  onChange={(e) => updateItem(item.key, { unitPrice: e.target.value })}
                />
              </label>
              <label className="field">
                <span className="field__label">금액</span>
                <input
                  className="input"
                  inputMode="numeric"
                  value={item.amount}
                  onChange={(e) => updateItem(item.key, { amount: e.target.value })}
                />
              </label>
              {/* 숫자 키패드에는 '-'가 없는 폰이 있어서, 할인 줄은 이 버튼으로 음수로 바꾼다 */}
              <button
                type="button"
                className="icon-button"
                aria-label={`${index + 1}번째 품목 금액 부호 바꾸기 (할인)`}
                title="할인이면 음수로"
                onClick={() => flipSign(item)}
              >
                ±
              </button>
            </div>
          </div>
        ))}
        <button type="button" className="button button--ghost" onClick={() => setField('items', [...state.items, emptyDraft()])}>
          + 품목 추가
        </button>
      </section>

      <section className="card">
        <dl className="summary">
          <dt>영수증 합계</dt>
          <dd>{total != null ? formatWon(total) : '—'}</dd>
          <dt>청구 금액 (품목 합계)</dt>
          <dd className="summary__strong">{formatWon(claimed)}</dd>
        </dl>
        {total != null && claimed < total && <p className="muted">영수증 중 {formatWon(total - claimed)}은 청구에서 빠져요.</p>}
        {total != null && claimed > total && <p className="error">청구 금액이 영수증 합계보다 커요. 금액을 확인하세요.</p>}
        {uncategorized > 0 && <p className="muted">계정과목을 안 정한 품목이 {uncategorized}개 있어요. 제출 전에 정해주세요.</p>}
      </section>

      {(formError || serverError) && <p className="error">{formError ?? errorMessage(serverError)}</p>}
      {saved && <p className="ok">저장했어요. 나중에 이어서 고칠 수 있어요.</p>}

      <div className="actions">
        <button type="button" className="button" onClick={handleSave} disabled={busy}>
          {save.isPending && !submit.isPending ? '저장 중…' : '임시 저장'}
        </button>
        <button type="button" className="button button--primary" onClick={handleSubmit} disabled={busy}>
          {submit.isPending ? '제출 중…' : '제출'}
        </button>
      </div>
      <button type="button" className="link-button link-button--danger" onClick={handleDelete} disabled={busy}>
        이 지출 삭제
      </button>
    </div>
  )
}
