import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
})

// 영수증 이미지처럼 임시 주소(blob:)를 담은 쿼리(meta.objectUrl)는 새 값으로 바뀌거나 캐시에서 빠질 때 해제 (메모리 누수 방지)
const objectUrls = new Map<string, string>()
queryClient.getQueryCache().subscribe((event) => {
  if (!event.query.meta?.objectUrl) return
  const hash = event.query.queryHash
  const current = (event.query.state.data as { url?: string } | undefined)?.url
  const previous = objectUrls.get(hash)
  if (event.type === 'removed') {
    if (previous) URL.revokeObjectURL(previous)
    objectUrls.delete(hash)
  } else if (current && current !== previous) {
    if (previous) URL.revokeObjectURL(previous)
    objectUrls.set(hash, current)
  }
})
