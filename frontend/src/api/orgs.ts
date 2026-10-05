import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api, unwrap } from './client'
import type { MembershipRole, OrgDetail } from './types'

export const orgKeys = {
  all: ['orgs'] as const,
  detail: (orgId: number) => ['orgs', orgId] as const,
  members: (orgId: number) => ['orgs', orgId, 'members'] as const,
}

/** 내가 속한 조직 목록 */
export function useMyOrgs() {
  return useQuery({
    queryKey: orgKeys.all,
    queryFn: async () => unwrap(await api.GET('/api/v1/orgs')),
  })
}

export function useOrg(orgId: number) {
  return useQuery({
    queryKey: orgKeys.detail(orgId),
    queryFn: async () => unwrap(await api.GET('/api/v1/orgs/{org_id}', { params: { path: { org_id: orgId } } })),
    retry: false, // 404(구성원 아님)는 다시 시도해도 같음
  })
}

export function useMembers(orgId: number) {
  return useQuery({
    queryKey: orgKeys.members(orgId),
    queryFn: async () =>
      unwrap(await api.GET('/api/v1/orgs/{org_id}/members', { params: { path: { org_id: orgId } } })),
  })
}

function useOrgEntered() {
  const queryClient = useQueryClient()
  return (org: OrgDetail) => {
    queryClient.setQueryData(orgKeys.detail(org.id), org)
    queryClient.invalidateQueries({ queryKey: orgKeys.all, exact: true })
  }
}

export function useCreateOrg() {
  const onSuccess = useOrgEntered()
  return useMutation({
    mutationFn: async (name: string) => unwrap(await api.POST('/api/v1/orgs', { body: { name } })),
    onSuccess,
  })
}

export function useJoinOrg() {
  const onSuccess = useOrgEntered()
  return useMutation({
    mutationFn: async (inviteCode: string) =>
      unwrap(await api.POST('/api/v1/orgs/join', { body: { invite_code: inviteCode } })),
    onSuccess,
  })
}

export function useRegenerateInviteCode(orgId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async () =>
      unwrap(await api.POST('/api/v1/orgs/{org_id}/invite-code', { params: { path: { org_id: orgId } } })),
    onSuccess: ({ invite_code }) =>
      queryClient.setQueryData<OrgDetail>(orgKeys.detail(orgId), (old) => (old ? { ...old, invite_code } : old)),
  })
}

export function useUpdateRole(orgId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ membershipId, role }: { membershipId: number; role: MembershipRole }) =>
      unwrap(
        await api.PATCH('/api/v1/orgs/{org_id}/members/{membership_id}', {
          params: { path: { org_id: orgId, membership_id: membershipId } },
          body: { role },
        }),
      ),
    // 내 역할이 바뀌었을 수도 있으니 조직 정보·목록도 새로
    onSuccess: () => queryClient.invalidateQueries({ queryKey: orgKeys.all }),
  })
}
