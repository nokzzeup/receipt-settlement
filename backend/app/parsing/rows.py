"""OCR 박스 → 행(row)·토큰 단위로 정리.

OCR 결과는 '줄'이 아니라 '박스' 단위다. 같은 행의 상품명·수량·금액이 따로따로 오기도 하고,
반대로 한 박스에 "합계 25,400"처럼 여러 단어가 붙어 오기도 한다. 둘 다 같은 방식으로 다루려고
1) y 좌표가 가까운 박스끼리 한 행으로 묶고 2) 박스 안 텍스트를 공백으로 나눠 토큰마다 x 위치를 어림한다.
"""

from dataclasses import dataclass
from statistics import median

from app.ocr.schemas import OcrRawResult

# 같은 행으로 볼 y 차이 (글자 높이 대비 비율)
ROW_TOLERANCE = 0.6


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


def _to_box(text: str, bbox: tuple[tuple[float, float], ...]) -> Box:
    xs = [p[0] for p in bbox]
    ys = [p[1] for p in bbox]
    return Box(text=text, left=min(xs), right=max(xs), top=min(ys), bottom=max(ys))


def group_rows(raw: OcrRawResult) -> list[Row]:
    """위→아래 순서의 행 목록. 행 안의 박스는 왼쪽→오른쪽"""
    boxes = [_to_box(line.text.strip(), line.bbox) for line in raw.lines if line.text.strip()]
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
