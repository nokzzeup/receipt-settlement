import { useState, type FormEvent } from 'react'
import { useCategories, useCreateCategory, useDeleteCategory, useUpdateCategory } from '../api/categories'
import { errorMessage } from '../api/client'
import type { Category } from '../api/types'
import { useFeedback } from '../feedback/context'
import { formatWon, parseInteger } from '../lib/format'
import { CategoryTile } from './CategoryTile'
import { Icon } from './Icon'
import { SkeletonRows } from './SkeletonRows'

type Props = { orgId: number; canManage: boolean }

/** 예산 입력칸 → 원 단위 정수 (빈칸 = 예산 없음). 잘못되면 문자열 에러 */
function parseBudget(value: string): number | null | string {
  const budget = parseInteger(value)
  if (budget === undefined || (budget !== null && budget < 0)) return '예산은 0 이상의 정수(원)로 입력하세요.'
  return budget
}

/** 조직 설정 > 계정과목·예산. 총무만 추가·수정·삭제 (줄을 누르면 그 자리에서 고침) */
export function CategorySettings({ orgId, canManage }: Props) {
  const { toast, confirm } = useFeedback()
  const categories = useCategories(orgId)
  const create = useCreateCategory(orgId)
  const update = useUpdateCategory(orgId)
  const remove = useDeleteCategory(orgId)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [adding, setAdding] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const mutationError = create.error ?? update.error ?? remove.error
  const busy = create.isPending || update.isPending || remove.isPending

  function resetErrors() {
    setFormError(null)
    create.reset()
    update.reset()
    remove.reset()
  }

  function startEdit(id: number | null) {
    resetErrors()
    setAdding(false)
    setEditingId(id)
  }

  function handleCreate(name: string, budgetText: string) {
    resetErrors()
    const budget = parseBudget(budgetText)
    if (typeof budget === 'string') return setFormError(budget)
    create.mutate(
      { name, budget_amount: budget },
      {
        onSuccess: () => {
          setAdding(false)
          toast(`'${name.trim()}' 계정과목을 추가했어요`)
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
      {
        onSuccess: () => {
          setEditingId(null)
          toast('저장했어요')
        },
      },
    )
  }

  async function handleDelete(category: Category) {
    resetErrors()
    const ok = await confirm({
      title: `'${category.name}' 계정과목을 삭제할까요?`,
      message: '이 계정과목을 쓰는 품목이 있으면 삭제할 수 없어요.',
      confirmLabel: '삭제',
      danger: true,
    })
    if (!ok) return
    remove.mutate(category.id, {
      onSuccess: () => {
        setEditingId(null)
        toast('삭제했어요')
      },
    })
  }

  return (
    <section className="card card--list" aria-label="계정과목 · 예산">
      <div className="card__head">
        <h2 className="card__title">계정과목 · 예산</h2>
        {!canManage && <span className="card__sub">총무만 바꿀 수 있어요</span>}
      </div>
      {categories.isPending && <SkeletonRows count={3} />}
      {categories.isError && <p className="message message--error">{errorMessage(categories.error)}</p>}
      {categories.data?.length === 0 && (
        <p className="caption" style={{ padding: '12px 8px' }}>
          계정과목이 없어요.{canManage && ' 아래에서 추가하세요.'}
        </p>
      )}
      <ul className="rows" style={{ marginTop: 6 }}>
        {categories.data?.map((category) =>
          editingId === category.id ? (
            <li key={category.id}>
              <CategoryEditor
                category={category}
                busy={busy}
                onSave={(name, budget) => handleSave(category, name, budget)}
                onCancel={() => startEdit(null)}
                onDelete={() => handleDelete(category)}
              />
            </li>
          ) : (
            <li key={category.id}>
              {canManage ? (
                <button
                  type="button"
                  className="row-item press"
                  onClick={() => startEdit(category.id)}
                  aria-label={`${category.name} 수정`}
                >
                  <CategoryRowContent category={category} />
                  <Icon name="chevronRight" size={20} className="row-item__chevron" />
                </button>
              ) : (
                <div className="row-item">
                  <CategoryRowContent category={category} />
                </div>
              )}
            </li>
          ),
        )}
      </ul>

      {canManage &&
        (adding ? (
          <CategoryEditor busy={busy} onSave={handleCreate} onCancel={() => setAdding(false)} />
        ) : (
          <button
            type="button"
            className="row-item press"
            style={{ color: 'var(--primary)' }}
            onClick={() => {
              startEdit(null)
              setAdding(true)
            }}
          >
            <span className="tile tile--md" style={{ background: 'transparent', border: '1.5px dashed #c3b6f7', color: 'var(--primary)' }}>
              <Icon name="plus" size={20} />
            </span>
            <span className="row-item__title">계정과목 추가</span>
          </button>
        ))}
      {(formError || mutationError) && (
        <p className="message message--error anim-rise" role="alert" style={{ padding: '4px 8px 12px' }}>
          <Icon name="alert" size={18} />
          {formError ?? errorMessage(mutationError)}
        </p>
      )}
    </section>
  )
}

function CategoryRowContent({ category }: { category: Category }) {
  return (
    <>
      <CategoryTile category={category} size="md" />
      <span className="row-item__main">
        <span className="row-item__title">{category.name}</span>
        <span className="row-item__sub">
          {category.budget_amount === null ? '예산 없음' : `예산 ${formatWon(category.budget_amount)}`}
        </span>
      </span>
    </>
  )
}

type EditorProps = {
  /** 없으면 새로 추가 */
  category?: Category
  busy: boolean
  onSave: (name: string, budget: string) => void
  onCancel: () => void
  onDelete?: () => void
}

function CategoryEditor({ category, busy, onSave, onCancel, onDelete }: EditorProps) {
  const [name, setName] = useState(category?.name ?? '')
  const [budget, setBudget] = useState(category?.budget_amount?.toString() ?? '')

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onSave(name, budget)
  }

  return (
    <form className="inline-form anim-fade" onSubmit={handleSubmit}>
      <div className="inline-form__fields">
        <input
          className="input"
          aria-label="계정과목 이름"
          placeholder="새 계정과목"
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={50}
          required
          autoFocus
        />
        <input
          className="input"
          aria-label="예산(원)"
          inputMode="numeric"
          placeholder={category ? '예산 없음' : '예산(선택)'}
          value={budget}
          onChange={(e) => setBudget(e.target.value)}
        />
      </div>
      <div className="btn-row">
        {onDelete && (
          <button type="button" className="btn btn--md btn--danger-text" style={{ flex: 'none' }} onClick={onDelete} disabled={busy}>
            삭제
          </button>
        )}
        <button type="button" className="btn btn--md btn--secondary" onClick={onCancel}>
          취소
        </button>
        <button className="btn btn--md btn--primary" type="submit" disabled={busy || !name.trim()}>
          {category ? '저장' : '추가'}
        </button>
      </div>
    </form>
  )
}
