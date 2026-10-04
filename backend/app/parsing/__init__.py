"""영수증 필드 파싱 (담당: 이성민). OcrRawResult → ReceiptFields"""

from app.parsing.parser import parse
from app.parsing.schemas import ReceiptFields, ReceiptItem

__all__ = ["ReceiptFields", "ReceiptItem", "parse"]
