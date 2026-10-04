"""정산 엔진 (5단계, 담당: 이성민) — 결제자별 환급 대상 집계, 환급 완료 처리, 계정별 집행액·잔액.

규칙: 이 모듈의 모든 계산 함수는 pytest 단위 테스트를 같이 작성한다.
- 금액은 int만 (ExpenseItem.amount 합계 기준)
- 환급 대상 = APPROVED 이면서 reimbursed_at IS NULL 인 지출
"""
