from abc import ABC, abstractmethod

from app.ocr.schemas import OcrRawResult


class OcrEngine(ABC):
    """OCR 엔진 인터페이스. 전처리(OpenCV)도 recognize 안에서 처리한다."""

    name: str

    @abstractmethod
    def recognize(self, image_bytes: bytes) -> OcrRawResult:
        """이미지 바이트 → OCR 원문(박스 단위 텍스트 + 신뢰도 + 좌표)."""
