"""OCR 엔진 출력 → 팀 계약 형식(OcrRawResult) 변환.

엔진마다 결과 모양이 달라도 여기서 OcrRawResult로 맞춘다. numpy 없이도 동작하게 작성
(numpy 배열은 .tolist()로 파이썬 리스트로 바꿔서 처리) → OCR 패키지가 없는 PC에서도 테스트 가능
"""

from collections.abc import Iterable, Sequence
from typing import Any

from app.ocr.schemas import OcrLine, OcrRawResult


def _plain(value: Any) -> Any:
    return value.tolist() if hasattr(value, "tolist") else value


def to_raw_result(engine: str, texts: Iterable[str], scores: Iterable[Any], polys: Iterable[Any]) -> OcrRawResult:
    """박스별 (글자, 신뢰도, 4점 좌표) → OcrRawResult.

    - 글자가 빈 박스는 뺀다 (PaddleOCR는 못 읽은 박스를 빈 문자열·신뢰도 0으로 돌려줌)
    - 좌표 4점 순서는 엔진이 좌상 → 우상 → 우하 → 좌하로 준다고 가정 (PaddleOCR 3.7 확인)
    """
    lines: list[OcrLine] = []
    for text, score, poly in zip(texts, scores, polys, strict=True):
        text = str(text).strip()
        if not text:
            continue
        points: Sequence[Sequence[float]] = _plain(poly)
        if len(points) != 4:
            continue  # 4점이 아닌 다각형은 계약 밖 → 버림
        bbox = tuple((float(x), float(y)) for x, y in points)
        confidence = min(max(float(_plain(score)), 0.0), 1.0)
        lines.append(OcrLine(text=text, confidence=confidence, bbox=bbox))
    return OcrRawResult(engine=engine, lines=lines)
