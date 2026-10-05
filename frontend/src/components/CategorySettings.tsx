import { useState, type FormEvent } from 'react'
import { useCategories, useCreateCategory, useDeleteCategory, useUpdateCategory } from '../api/categories'
import { errorMessage } from '../api/client'
import type { Category } from '../api/types'
import { formatWon, parseInteger } from '../lib/format'

type Props = { orgId: number; canManage: boolean }

/** 예산 입력칸 → 원 단위 정수 (빈칸 = 예산 없음). 잘못되면 문자열 에러 */
function parseBudget(value: string): number | null | string {
  const budget = parseInteger(value)
  if (budget === undefined || (budget !== null && budget < 0)) return '예산은 0 이상의 정수(원)로 입력하세요.'
  return budget
}

/** 조직 설정 > 계정과목·예산. 총무만 추가·수정·삭제 */
export function CategorySettings({ orgId, canManage }: Props) {
  const categories = useCategories(orgId)
  const create = useCreateCategory(orgId)
  const update = useUpdateCategory(orgId)
  const remove = useDeleteCategory(orgId)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [newName, setNewName] = useState('')
  const [newBudget, setNewBudget] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  const mutationError = create.error ?? update.error ?? remove.error
  const busy = create.isPending || update.isPending || remove.isPending

  function resetErrors() {
    setFormError(null)
    create.reset()
    update.reset()
    remove.reset()
  }

  function handleCreate(e: FormEvent) {
    e.preventDefault()
    resetErrors()
    const budget = parseBudget(newBudget)
    if (typeof budget === 'string') return setFormError(budget)
    create.mutate(
      { name: newName, budget_amount: budget },
      {
        onSuccess: () => {
          setNewName('')
          setNewBudget('')
        },
      },
    )
  }

  function handleSave(category: Category, name: string, budgetText: string) {
    resetErrors()
    const budget = parseBudget(budgetText)
    if (typeof budget === 'string') return setFormError(budget)
    update.mutate(
      { categoryId: category.id, body: { name, budget_amount: budget } },
      { onSuccess: () => setEditingId(null) },
    )
  }

  function handleDelete(category: Category) {
    resetErrors()
    if (window.confirm(`'${category.name}' 계정과목을 삭제할까요?`)) remove.mutate(category.id)
  }

  return (
    <section className="card">
      <h2 className="card__title">계정과목 · 예산</h2>
      {categories.isPending && <p className="muted">불러오는 중…</p>}
      {categories.isError && <p className="error">{errorMessage(categories.error)}</p>}
      {categories.data?.length === 0 && <p className="muted">계정과목이 없어요.{canManage && ' 아래에서 추가하세요.'}</p>}
      {categories.data && categories.data.length > 0 && (
        <ul className="list">
          {categories.data.map((category) =>
            editingId === category.id ? (
              <li key={category.id}>
                <CategoryEditor
                  category={category}
                  busy={busy}
                  onSave={(name, budget) => handleSave(category, name, budget)}
                  onCancel={() => setEditingId(null)}
                />
              </li>
            ) : (
              <li key={category.id} className="list__item">
                <span className="list__main">
                  {category.name}
                  <span className="list__sub">
                    {category.budget_amount === null ? '예산 없음' : `예산 ${formatWon(category.budget_amount)}`}
                  </span>
                </span>
                {canManage && (
                  <span className="row">
                    <button type="button" className="link-button" onClick={() => setEditingId(category.id)}>
                      수정
                    </button>
                    <button
                      type="button"
                      className="link-button link-button--danger"
                      onClick={() => handleDelete(category)}
                      disabled={busy}
                    >
                      삭제
                    </button>
                  </span>
                )}
              </li>
            ),
          )}
        </ul>
      )}

      {canManage && (
        <form className="category-form" onSubmit={handleCreate}>
          <input
            className="input"
            placeholder="새 계정과목"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            maxLength={50}
            required
          />
          <input
            className="input"
            inputMode="numeric"
            placeholder="예산(선택)"
            value={newBudget}
            onChange={(e) => setNewBudget(e.target.value)}
          />
          <button className="button" type="submit" disabled={busy || !newName.trim()}>
            추가
          </button>
        </form>
      )}
      {(formError || mutationError) && <p className="error">{formError ?? errorMessage(mutationError)}</p>}
      {!canManage && <p className="muted">계정과목은 총무만 바꿀 수 있어요.</p>}
    </section>
  )
}

type EditorProps = {
  category: Category
  busy: boolean
  onSave: (name: string, budget: string) => void
  onCancel: () => void
}

function CategoryEditor({ category, busy, onSave, onCancel }: EditorProps) {
  const [name, setName] = useState(category.name)
  const [budget, setBudget] = useState(category.budget_amount?.toString() ?? '')

  return (
    <form
      className="category-form category-form--edit"
      onSubmit={(e) => {
        e.preventDefault()
        onSave(name, budget)
      }}
    >
      <input
        className="input"
        aria-label="계정과목 이름"
        value={name}
        onChange={(e) => setName(e.target.value)}
        maxLength={50}
        required
      />
      <input
        className="input"
        aria-label="예산(원)"
        inputMode="numeric"
        placeholder="예산 없음"
        value={budget}
        onChange={(e) => setBudget(e.target.value)}
      />
      <span className="row">
        <button className="button" type="submit" disabled={busy || !name.trim()}>
          저장
        </button>
        <button className="button button--ghost" type="button" onClick={onCancel}>
          취소
        </button>
      </span>
    </form>
  )
}
