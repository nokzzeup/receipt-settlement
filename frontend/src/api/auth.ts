import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query'
import { clearToken, getToken, setToken } from '../auth/token'
import { api, unwrap } from './client'
import type { components } from './schema'

type S = components['schemas']

/** 로그인한 내 정보 */
export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: async () => unwrap(await api.GET('/api/v1/auth/me')),
    enabled: getToken() !== null,
    staleTime: Infinity,
  })
}

function useAuthSuccess() {
  const queryClient = useQueryClient()
  return (data: S['TokenResponse']) => {
    setToken(data.access_token)
    queryClient.clear() // 이전 사용자의 캐시가 남지 않게
    queryClient.setQueryData(['me'], data.user)
  }
}

export function useLogin() {
  const onSuccess = useAuthSuccess()
  return useMutation({
    mutationFn: async (body: S['LoginRequest']) => unwrap(await api.POST('/api/v1/auth/login', { body })),
    onSuccess,
  })
}

export function useSignup() {
  const onSuccess = useAuthSuccess()
  return useMutation({
    mutationFn: async (body: S['SignupRequest']) => unwrap(await api.POST('/api/v1/auth/signup', { body })),
    onSuccess,
  })
}

export function logout(queryClient: QueryClient) {
  clearToken()
  queryClient.clear()
}
