from datetime import date

from pydantic import BaseModel

from app.schemas.expense import PersonOut


class ReportCategoryOut(BaseModel):
    category_id: int | None  # null = 미분류
    name: str
    amount: int  # 기간 안 승인된 지출에서 이 계정과목 금액
    item_count: int
    budget: int | None  # 지금 설정된 예산 (참고용)


class ReportPayerOut(BaseModel):
    payer: PersonOut
    amount: int  # 승인된 금액
    reimbursed: int  # 그중 돌려준 금액
    unreimbursed: int
    expense_count: int


class ReportOut(BaseModel):
    """기간별 리포트: 결제일이 기간 안(한국 날짜, 양 끝 포함)이고 승인된 지출"""

    start: date
    end: date
    approved_count: int
    approved_amount: int
    reimbursed_amount: int
    unreimbursed_amount: int
    awaiting_count: int  # 같은 기간 승인 대기 (합계에 안 들어감)
    awaiting_amount: int
    categories: list[ReportCategoryOut]  # 금액 큰 순 (쓴 계정과목만)
    payers: list[ReportPayerOut]  # 금액 큰 순
