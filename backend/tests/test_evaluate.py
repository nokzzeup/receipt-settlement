"""정확도 측정 도구(npm run ocr:eval): 채점 기준 + 저장해 둔 OCR 결과로 PaddleOCR 없이 채점"""

import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest

from app.core.timezone import KST
from app.ocr import OcrRawResult
from app.ocr.paddle import ENGINE_SIGNATURE
from app.ops import evaluate
from app.parsing import ReceiptFields, ReceiptItem

FIXTURES = Path(__file__).parent / "fixtures" / "paddle"


def fields(**changes: object) -> ReceiptFields:
    base = ReceiptFields(
        store_name="이마트24 강남역점",
        paid_at=datetime(2026, 9, 30, 18, 42, 17, tzinfo=KST),
        total_amount=8800,
        items=[
            ReceiptItem(name="삼다수 2L", quantity=6, unit_price=1300, amount=7800),
            ReceiptItem(name="행사할인", amount=-1000),
            ReceiptItem(name="종이컵", amount=2000),
        ],
    )
    return base.model_copy(update=changes)


def test_score_ignores_spaces_seconds_and_unit_price() -> None:
    label = fields()
    got = fields(
        store_name="이마트24강남역점",  # OCR이 띄어쓰기를 빼먹음
        paid_at=datetime(2026, 9, 30, 18, 42, 59, tzinfo=KST),  # 초만 다름
        items=[
            ReceiptItem(name="삼다수2L", quantity=6, unit_price=None, amount=7800),  # 단가는 채점 안 함
            ReceiptItem(name="행사할인", amount=-1000),
            ReceiptItem(name="종이컵", amount=2000),
        ],
    )
    result = evaluate.score(label, got)
    assert (result.store_name, result.paid_at, result.total_amount) == (True, True, True)
    assert result.items_exact


def test_score_counts_wrong_and_extra_items() -> None:
    got = fields(
        total_amount=8000,
        items=[
            ReceiptItem(name="삼다수 2L", quantity=6, amount=7800),
            ReceiptItem(name="종이컵", amount=200),  # 금액을 잘못 읽음
            ReceiptItem(name="받은금액", amount=10000),  # 품목이 아닌 줄을 품목으로
        ],
    )
    result = evaluate.score(fields(), got)
    assert result.total_amount is False
    assert (result.items_expected, result.items_found, result.items_matched) == (3, 3, 1)
    assert not result.items_exact


@pytest.fixture
def dataset(tmp_path: Path) -> Path:
    """사진 + 정답 + (이미 인식해 둔) OCR 결과가 있는 dataset 폴더"""
    root = tmp_path / "dataset"
    (root / "images").mkdir(parents=True)
    (root / "labels").mkdir()
    for name in ("mart", "cvs", "cafe"):
        image = root / "images" / f"{name}.jpg"
        image.write_bytes(f"사진 {name}".encode())
        shutil.copy(FIXTURES / f"{name}.label.json", root / "labels" / f"{name}.json")
        raw = OcrRawResult.model_validate_json((FIXTURES / f"{name}.ocr.json").read_text(encoding="utf-8"))
        sample = evaluate.Sample(name, image, ReceiptFields())
        evaluate.save_cached(root, sample, ENGINE_SIGNATURE, raw, seconds=1.0)
    return root


def test_eval_uses_cached_ocr_without_paddle(dataset: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert evaluate.main(["--dataset", str(dataset)]) == 0
    out = capsys.readouterr().out
    assert "=== 3장 채점 ===" in out
    assert "합계        100.0%" in out
    assert "품목 재현율 100.0%" in out


def test_cache_is_ignored_when_photo_or_engine_changes(dataset: Path) -> None:
    sample = evaluate.find_samples(dataset, ["cvs"])[0][0]
    assert evaluate.load_cached(dataset, sample, ENGINE_SIGNATURE) is not None
    assert evaluate.load_cached(dataset, sample, ENGINE_SIGNATURE + "-changed") is None
    sample.image.write_bytes(b"other photo")
    assert evaluate.load_cached(dataset, sample, ENGINE_SIGNATURE) is None


def test_missing_photo_and_bad_label_are_reported(dataset: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (dataset / "labels" / "lost.json").write_text(json.dumps({"total_amount": 1}), encoding="utf-8")
    (dataset / "images" / "broken.jpg").write_bytes(b"x")
    (dataset / "labels" / "broken.json").write_text('{"total_amount": "만원"}', encoding="utf-8")
    samples, warnings = evaluate.find_samples(dataset, [])
    assert sorted(s.name for s in samples) == ["cafe", "cvs", "mart"]
    assert any("lost" in w and "사진이 없어서" in w for w in warnings)
    assert any("broken" in w and "라벨 형식 오류" in w for w in warnings)
