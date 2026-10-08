"""실제 PaddleOCR 출력으로 파서 회귀 테스트.

tests/fixtures/paddle/*.ocr.json = 시험 영수증 사진을 실제 PaddleOCR(app/ocr/paddle.py 설정)로 인식한 결과(마스킹 후),
*.label.json = 정답. 채점 기준은 정확도 측정 도구(npm run ocr:eval)와 같다 (가게명·품목명 띄어쓰기 무시).
실제 영수증으로 파서를 고칠 때 이 샘플들이 계속 통과하는지 같이 확인한다.
"""

from pathlib import Path

import pytest

from app.ocr import OcrRawResult
from app.ops.evaluate import score
from app.parsing import ReceiptFields, parse

FIXTURES = Path(__file__).parent / "fixtures" / "paddle"


def load(name: str) -> tuple[OcrRawResult, ReceiptFields]:
    raw = OcrRawResult.model_validate_json((FIXTURES / f"{name}.ocr.json").read_text(encoding="utf-8"))
    label = ReceiptFields.model_validate_json((FIXTURES / f"{name}.label.json").read_text(encoding="utf-8"))
    return raw, label


@pytest.mark.parametrize("name", ["mart", "cvs", "cafe"])
def test_parser_reads_real_paddle_output(name: str) -> None:
    raw, label = load(name)
    got = parse(raw)
    result = score(label, got)

    assert result.store_name, (label.store_name, got.store_name)
    assert result.paid_at, (label.paid_at, got.paid_at)
    assert result.total_amount, (label.total_amount, got.total_amount)
    assert result.items_exact, (label.items, got.items)


def test_real_output_was_masked_before_saving() -> None:
    for file in FIXTURES.glob("*.ocr.json"):
        raw = OcrRawResult.model_validate_json(file.read_text(encoding="utf-8"))
        for line in raw.lines:
            if "카드번호" in line.text:
                assert sum(ch.isdigit() for ch in line.text) <= 4, line.text
