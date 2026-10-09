import { useQuery } from '@tanstack/react-query'
import { api, unwrap } from './client'

export const reportKeys = {
  summary: (orgId: number, start: string, end: string) => ['orgs', orgId, 'reports', start, end] as const,
}

/** 기간별 리포트 (총무·승인자). 기간 = 결제일 기준 'YYYY-MM-DD' 두 개, 승인된 지출만 */
export function useReport(orgId: number, start: string, end: string, enabled: boolean) {
  return useQuery({
    queryKey: reportKeys.summary(orgId, start, end),
    queryFn: async () =>
      unwrap(
        await api.GET('/api/v1/orgs/{org_id}/reports', { params: { path: { org_id: orgId }, query: { start, end } } }),
      ),
    enabled,
  })
}

/** 엑셀 파일 받기 (로그인 토큰을 붙여야 해서 <a href> 대신 받아서 저장) */
export async function downloadReport(orgId: number, start: string, end: string, filename: string): Promise<void> {
  const blob = unwrap(
    await api.GET('/api/v1/orgs/{org_id}/reports/export', {
      params: { path: { org_id: orgId }, query: { start, end } },
      parseAs: 'blob',
    }),
  ) as Blob
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  document.body.append(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(href), 10_000) // 바로 지우면 일부 브라우저에서 저장이 끊김
}
