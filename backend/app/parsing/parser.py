from app.ocr.schemas import OcrRawResult
from app.parsing.schemas import ReceiptFields


def parse(raw: OcrRawResult) -> ReceiptFields:
    """OCR 원문 → 영수증 필드. (3단계 구현 예정, 담당: 이성민) 지금은 빈 결과를 반환한다.

    구현 메모
    - 결과가 '줄' 단위가 아니라 '박스' 단위로 온다 → bbox의 y 좌표로 같은 행끼리 묶기
    - "1,200" → 1200 (int). float 금지
    - 합계/부가세/카드번호/승인번호 줄은 품목에서 제외
    - 할인 줄(음수 금액)을 품목으로 둘지 별도 처리할지 결정 필요
    - MockOcrEngine 샘플로 바로 테스트 가능: parse(MockOcrEngine().recognize(b""))
    """
    return ReceiptFields()
