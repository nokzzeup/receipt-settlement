"""실제 OCR 엔진 주변부 — PaddleOCR가 설치되지 않은 PC(팀원 대부분)에서도 돌아가는 테스트"""

from collections.abc import Iterator

import pytest

from app.core.config import settings
from app.ocr import factory
from app.ocr.convert import to_raw_result


class FakeArray:
    """numpy 배열 흉내 (tolist만)"""

    def __init__(self, value: object) -> None:
        self.value = value

    def tolist(self) -> object:
        return self.value


def test_to_raw_result_converts_and_filters() -> None:
    square = [[0, 0], [10, 0], [10, 5], [0, 5]]
    result = to_raw_result(
        "paddle",
        texts=["합계 25,400", "  ", "삼각형"],
        scores=[FakeArray(0.97), 0.0, 1.2],
        polys=[FakeArray(square), square, [[0, 0], [1, 1], [2, 2]]],
    )
    assert result.engine == "paddle"
    # 빈 글자 박스, 4점이 아닌 박스는 빠짐
    assert [line.text for line in result.lines] == ["합계 25,400"]
    assert result.lines[0].confidence == pytest.approx(0.97)
    assert result.lines[0].bbox == ((0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0))


def test_confidence_is_clamped() -> None:
    result = to_raw_result("x", ["a", "b"], [1.5, -0.2], [[[0, 0], [1, 0], [1, 1], [0, 1]]] * 2)
    assert [line.confidence for line in result.lines] == [1.0, 0.0]


@pytest.fixture
def paddle_setting(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(settings, "ocr_engine", "paddle")
    factory.get_ocr_engine.cache_clear()
    yield
    factory.get_ocr_engine.cache_clear()


def test_paddle_failure_falls_back_to_manual_input(paddle_setting: None, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ocr import paddle

    def broken_init(self: object) -> None:
        raise RuntimeError("PaddleOCR가 설치돼 있지 않습니다")

    monkeypatch.setattr(paddle.PaddleOcrEngine, "__init__", broken_init)
    engine = factory.get_ocr_engine()

    # 서버는 뜨고 업로드도 되지만, 인식은 실패로 처리 → 사용자가 직접 입력
    assert engine.name == "unavailable"
    with pytest.raises(RuntimeError, match="설치돼 있지 않습니다"):
        engine.recognize(b"")


def test_engine_signature_does_not_need_paddle() -> None:
    from app.ocr.paddle import ENGINE_SIGNATURE

    assert "paddleocr-3.7.0" in ENGINE_SIGNATURE
