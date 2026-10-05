import { useParams } from 'react-router'

/** URL의 :orgId를 숫자로. 숫자가 아니면 NaN */
export function useOrgId(): number {
  return Number(useParams().orgId)
}
