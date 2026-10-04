import { useQuery } from '@tanstack/react-query'
import { api, ApiError } from './client'

/** 백엔드·DB 연결 상태. API 훅은 이 파일처럼 기능별로 src/api/*.ts 에 만든다. */
export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const { data, error, response } = await api.GET('/api/v1/health')
      if (data) return data
      // DB만 죽은 경우(503)도 응답 본문으로 상태를 보여줌
      if (response.status === 503 && error) return error
      throw new ApiError(response.status, error)
    },
    retry: false,
  })
}
