// 여러 파일에서 같이 쓰는 쿼리 키 (서로 import하다 순환이 생기지 않게 따로 둠)

export const settlementKeys = {
  summary: (orgId: number) => ['orgs', orgId, 'settlement'] as const,
}
