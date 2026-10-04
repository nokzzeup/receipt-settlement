"""OCR 결과 스키마 — 팀 합의 계약. 합의 없이 바꾸지 않는다. (ocr ↔ parsing 경계)

OcrRawResult = { engine: str, lines: [{ text: str, confidence: float, bbox: [[x,y] x 4] }] }
"""

from pydantic import BaseModel, Field

Point = tuple[float, float]


class OcrLine(BaseModel):
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    # 이미지 픽셀 좌표 4점. 순서: 좌상 → 우상 → 우하 → 좌하 (엔진 구현체가 이 순서로 맞춰서 반환)
    bbox: tuple[Point, Point, Point, Point]


class OcrRawResult(BaseModel):
    engine: str  # "mock" | "paddle" ...
    lines: list[OcrLine]
