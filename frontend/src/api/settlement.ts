import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from './client'
import { expenseKeys } from './expenses'
import { settlementKeys } from './keys'

/** 정산 요약: 결제자별 돌려줄 돈(총무·승인자는 전체, 구성원은 내 몫) + 계정별 예산 사용 */
export function useSettlement(orgId: number) {
  return useQuery({
    queryKey: settlementKeys.summary(orgId),
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/orgs/{org_id}/settlement', { params: { path: { org_id: orgId } } })),
  })
}

/** 결제자 한 명에게 보낸 것으로 한 번에 표시 (총무). 화면에서 본 지출 목록 그대로 보낸다 */
export function useBulkReimburse(orgId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ payerId, expenseIds }: { payerId: number; expenseIds: number[] }) =>
      unwrap(
        await api.POST('/api/v1/orgs/{org_id}/settlement/reimburse', {
          params: { path: { org_id: orgId } },
          body: { payer_membership_id: payerId, expense_ids: expenseIds },
        }),
      ),
    onSettled: () => {
      // 성공이든 409(그 사이 바뀜)든 최신 상태로
      queryClient.invalidateQueries({ queryKey: settlementKeys.summary(orgId) })
      queryClient.invalidateQueries({ queryKey: expenseKeys.list(orgId), exact: true })
      // 각 지출 상세 (['orgs', id, 'expenses', expenseId]) — 원본 이미지 캐시는 그대로
      queryClient.invalidateQueries({
        predicate: ({ queryKey }) => queryKey.length === 4 && queryKey[1] === orgId && queryKey[2] === 'expenses',
      })
    },
  })
}
