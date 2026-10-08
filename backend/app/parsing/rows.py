"""OCR 박스 → 행(row)·토큰 단위로 정리.

OCR 결과는 '줄'이 아니라 '박스' 단위다. 같은 행의 상품명·수량·금액이 따로따로 오기도 하고,
반대로 한 박스에 "합계 25,400"처럼 여러 단어가 붙어 오기도 한다. 둘 다 같은 방식으로 다루려고
0) 사진이 기울어 있으면 박스 좌표를 그만큼 되돌리고 (비스듬히 찍으면 오른쪽 금액 열이 한 줄 위/아래로 보임)
1) y 좌표가 가까운 박스끼리 한 행으로 묶고 2) 박스 안 텍스트를 공백으로 나눠 토큰마다 x 위치를 어림한다.
"""

import math
from dataclasses import dataclass
from statistics import median

from app.ocr.schemas import OcrRawResult

# 같은 행으로 볼 y 차이 (글자 높이 대비 비율)
ROW_TOLERANCE = 0.6
# 이보다 크게 기울어진 값은 추정이 잘못된 것으로 보고 보정하지 않음
MAX_SKEW_DEGREES = 20


@dataclass(frozen=True)
class Box:
    text: str
    left: float
    right: float
    top: float
    bottom: float

    @property
    def center_y(self) -> float:
        return (self.top + self.bottom) / 2

    @property
    def height(self) -> float:
        return max(self.bottom - self.top, 1.0)


@dataclass(frozen=True)
class Token:
    text: str
    center_x: float


@dataclass
class Row:
    boxes: list[Box]

    @property
    def center_y(self) -> float:
        return sum(b.center_y for b in self.boxes) / len(self.boxes)

    @property
    def height(self) -> float:
        return median(b.height for b in self.boxes)

    @property
    def text(self) -> str:
        return " ".join(b.text for b in self.boxes)

    def tokens(self) -> list[Token]:
        """공백 기준 토큰 + 대략적인 x 중심 (박스 폭을 글자 수 비율로 나눠서 어림)"""
        result: list[Token] = []
        for box in self.boxes:
            length = len(box.text)
            start = 0
            for part in box.text.split():
                offset = box.text.index(part, start)
                start = offset + len(part)
                ratio = (offset + len(part) / 2) / length
                result.append(Token(part, box.left + (box.right - box.left) * ratio))
        result.sort(key=lambda t: t.center_x)
        return result


def estimate_skew(raw: OcrRawResult) -> float:
    """사진 기울기(라디안) = 글자 박스 윗변 각도의 폭 가중 중앙값.

    짧은 박스(숫자 한두 글자)는 각도가 부정확해서 뺀다. 원근 때문에 위아래 각도가 조금 달라도 중앙값이라 안정적
    """
    samples: list[tuple[float, float]] = []
    for line in raw.lines:
        (x0, y0), (x1, y1), _, (x3, y3) = line.bbox
        width = math.hypot(x1 - x0, y1 - y0)
        height = math.hypot(x3 - x0, y3 - y0)
        if line.text.strip() and width >= 2.5 * max(height, 1.0):
            samples.append((math.atan2(y1 - y0, x1 - x0), width))
    if not samples:
        return 0.0
    samples.sort()
    half = sum(weight for _, weight in samples) / 2
    total = 0.0
    for angle, weight in samples:
        total += weight
        if total >= half:
            return angle if abs(angle) <= math.radians(MAX_SKEW_DEGREES) else 0.0
    return 0.0


def _to_box(text: str, bbox: tuple[tuple[float, float], ...], skew: float) -> Box:
    # 기울기만큼 반대로 돌린 좌표 → 같은 행의 박스가 같은 높이에 오게
    cos, sin = math.cos(skew), math.sin(skew)
    points = [(x * cos + y * sin, -x * sin + y * cos) for x, y in bbox]
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return Box(text=text, left=min(xs), right=max(xs), top=min(ys), bottom=max(ys))


def group_rows(raw: OcrRawResult) -> list[Row]:
    """위→아래 순서의 행 목록. 행 안의 박스는 왼쪽→오른쪽"""
    skew = estimate_skew(raw)
    boxes = [_to_box(line.text.strip(), line.bbox, skew) for line in raw.lines if line.text.strip()]
    boxes.sort(key=lambda b: b.center_y)
    rows: list[Row] = []
    for box in boxes:
        if rows:
            last = rows[-1]
            if abs(box.center_y - last.center_y) <= ROW_TOLERANCE * min(box.height, last.height):
                last.boxes.append(box)
                continue
        rows.append(Row([box]))
    for row in rows:
        row.boxes.sort(key=lambda b: b.left)
    return rows


def row_texts(raw: OcrRawResult) -> list[str]:
    """화면에 '인식된 원문'으로 보여줄 행 단위 텍스트"""
    return [row.text for row in group_rows(raw)]
