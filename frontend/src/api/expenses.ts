import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from './client'
import type { ExpenseDetail, ExpenseUpdate } from './types'

export const expenseKeys = {
  list: (orgId: number) => ['orgs', orgId, 'expenses'] as const,
  detail: (orgId: number, expenseId: number) => ['orgs', orgId, 'expenses', expenseId] as const,
  image: (orgId: number, expenseId: number) => ['orgs', orgId, 'expenses', expenseId, 'image'] as const,
}

const pathOf = (orgId: number, expenseId: number) => ({ path: { org_id: orgId, expense_id: expenseId } })

/** 내가 볼 수 있는 지출 목록 (총무·승인자는 전체, 구성원은 내가 올렸거나 결제자인 것) */
export function useExpenses(orgId: number) {
  return useQuery({
    queryKey: expenseKeys.list(orgId),
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/orgs/{org_id}/expenses', { params: { path: { org_id: orgId } } })),
  })
}

export function useExpense(orgId: number, expenseId: number) {
  return useQuery({
    queryKey: expenseKeys.detail(orgId, expenseId),
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/orgs/{org_id}/expenses/{expense_id}', { params: pathOf(orgId, expenseId) })),
    retry: false, // 404(못 보는 지출)는 다시 시도해도 같음
  })
}

/** 지출 하나가 바뀌었을 때: 상세는 응답으로 바로 교체, 목록은 다시 불러오기 */
function useExpenseChanged(orgId: number) {
  const queryClient = useQueryClient()
  return (expense: ExpenseDetail) => {
    queryClient.setQueryData(expenseKeys.detail(orgId, expense.id), expense)
    queryClient.invalidateQueries({ queryKey: expenseKeys.list(orgId), exact: true })
  }
}

/** 영수증 사진 업로드 → OCR → 작성 중 지출 생성 */
export function useUploadReceipt(orgId: number) {
  const onSuccess = useExpenseChanged(orgId)
  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('image', file)
      return unwrap(
        await api.POST('/api/v1/orgs/{org_id}/receipts', {
          params: { path: { org_id: orgId } },
          // 파일은 JSON이 아니라 FormData로 보낸다 (Content-Type·boundary는 브라우저가 붙임).
          // 자동 생성 타입은 파일을 string으로 표시해서 형변환이 필요함
          body: formData as unknown as { image: string },
        }),
      )
    },
    onSuccess,
  })
}

export function useSaveExpense(orgId: number, expenseId: number) {
  const onSuccess = useExpenseChanged(orgId)
  return useMutation({
    mutationFn: async (body: ExpenseUpdate) =>
      unwrap(await api.PUT('/api/v1/orgs/{org_id}/expenses/{expense_id}', { params: pathOf(orgId, expenseId), body })),
    onSuccess,
  })
}

export function useSubmitExpense(orgId: number, expenseId: number) {
  const onSuccess = useExpenseChanged(orgId)
  return useMutation({
    mutationFn: async () =>
      unwrap(
        await api.POST('/api/v1/orgs/{org_id}/expenses/{expense_id}/submit', { params: pathOf(orgId, expenseId) }),
      ),
    onSuccess,
  })
}

export function useDeleteExpense(orgId: number, expenseId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () =>
      unwrap(await api.DELETE('/api/v1/orgs/{org_id}/expenses/{expense_id}', { params: pathOf(orgId, expenseId) })),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: expenseKeys.detail(orgId, expenseId) })
      queryClient.invalidateQueries({ queryKey: expenseKeys.list(orgId), exact: true })
    },
  })
}

/**
 * 영수증 원본 이미지 → 화면에 쓸 임시 주소(blob:). <img src>로는 로그인 토큰을 못 보내서
 * 토큰을 붙여 받은 뒤 임시 주소로 바꿔 쓴다. 임시 주소 해제는 queryClient.ts가 캐시에서 빠질 때 처리.
 */
export function useReceiptImage(orgId: number, expenseId: number) {
  return useQuery({
    queryKey: expenseKeys.image(orgId, expenseId),
    queryFn: async () => {
      const blob = unwrap(
        await api.GET('/api/v1/orgs/{org_id}/expenses/{expense_id}/image', {
          params: pathOf(orgId, expenseId),
          parseAs: 'blob',
        }),
      ) as Blob
      return { url: URL.createObjectURL(blob) }
    },
    meta: { objectUrl: true },
    staleTime: Infinity, // 같은 지출의 원본 이미지는 바뀌지 않음
    retry: false,
  })
}
