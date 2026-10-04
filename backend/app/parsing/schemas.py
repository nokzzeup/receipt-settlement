"""영수증 필드 스키마 — 팀 합의 계약. 합의 없이 바꾸지 않는다. (parsing 결과 = 확인·수정 화면의 초기값)

ReceiptFields = { store_name, paid_at, total_amount, items: [{ name, quantity, unit_price, amount }] }

- 금액·수량은 정수(int)만 허용 (StrictInt: 1200.0 같은 float나 "1200" 문자열이 들어오면 에러)
- paid_at은 timezone-aware만 허용 → 영수증 시각에 KST(app.core.timezone.KST)를 붙여서 넣을 것
- 못 읽은 값은 None으로 두고 사용자가 화면에서 채운다
"""

from pydantic import AwareDatetime, BaseModel, Field, StrictInt


class ReceiptItem(BaseModel):
    name: str
    quantity: StrictInt = 1
    unit_price: StrictInt | None = None  # 영수증에 단가가 안 찍히면 None
    amount: StrictInt  # 이 품목의 금액(원)


class ReceiptFields(BaseModel):
    store_name: str | None = None
    paid_at: AwareDatetime | None = None
    total_amount: StrictInt | None = None
    items: list[ReceiptItem] = Field(default_factory=list)
