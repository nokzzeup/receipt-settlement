import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from './client'
import type { CategoryCreate, CategoryUpdate } from './types'

export const categoryKeys = {
  list: (orgId: number) => ['orgs', orgId, 'categories'] as const,
}

/** 조직의 계정과목 (만든 순서) */
export function useCategories(orgId: number) {
  return useQuery({
    queryKey: categoryKeys.list(orgId),
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/orgs/{org_id}/categories', { params: { path: { org_id: orgId } } })),
  })
}

function useRefreshCategories(orgId: number) {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: categoryKeys.list(orgId) })
}

export function useCreateCategory(orgId: number) {
  const onSuccess = useRefreshCategories(orgId)
  return useMutation({
    mutationFn: async (body: CategoryCreate) =>
      unwrap(await api.POST('/api/v1/orgs/{org_id}/categories', { params: { path: { org_id: orgId } }, body })),
    onSuccess,
  })
}

export function useUpdateCategory(orgId: number) {
  const onSuccess = useRefreshCategories(orgId)
  return useMutation({
    mutationFn: async ({ categoryId, body }: { categoryId: number; body: CategoryUpdate }) =>
      unwrap(
        await api.PATCH('/api/v1/orgs/{org_id}/categories/{category_id}', {
          params: { path: { org_id: orgId, category_id: categoryId } },
          body,
        }),
      ),
    onSuccess,
  })
}

export function useDeleteCategory(orgId: number) {
  const onSuccess = useRefreshCategories(orgId)
  return useMutation({
    mutationFn: async (categoryId: number) =>
      unwrap(
        await api.DELETE('/api/v1/orgs/{org_id}/categories/{category_id}', {
          params: { path: { org_id: orgId, category_id: categoryId } },
        }),
      ),
    onSuccess,
  })
}
