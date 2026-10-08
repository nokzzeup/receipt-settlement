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


# --- Windows: Visual C++ 재배포 패키지 확인 (2026-10-08 팀 노트북에서 _pyclipper DLL 에러로 실제 발생) ---


def test_vc_runtime_check_is_skipped_outside_windows() -> None:
    from app.ocr import winprereq

    assert winprereq.missing_runtime_dlls(platform="linux") == []
    assert winprereq.missing_runtime_dlls(platform="darwin") == []


def test_vc_runtime_check_reports_dlls_that_fail_to_load(monkeypatch: pytest.MonkeyPatch) -> None:
    import ctypes

    from app.ocr import winprereq

    def fake_windll(name: str) -> object:
        if name == "msvcp140.dll":
            raise OSError(126, "지정된 모듈을 찾을 수 없습니다")
        return object()

    monkeypatch.setattr(ctypes, "WinDLL", fake_windll, raising=False)  # 리눅스·맥 ctypes엔 WinDLL이 없음
    assert winprereq.missing_runtime_dlls(platform="win32") == ["msvcp140.dll"]


def test_vc_runtime_check_command_explains_how_to_fix(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from app.ocr import winprereq

    monkeypatch.setattr(winprereq, "missing_runtime_dlls", lambda: ["msvcp140.dll", "vcomp140.dll"])
    assert winprereq.main() == 1
    out = capsys.readouterr().out
    assert "msvcp140.dll, vcomp140.dll" in out
    assert winprereq.VC_REDIST_URL in out

    monkeypatch.setattr(winprereq, "missing_runtime_dlls", lambda: [])
    assert winprereq.main() == 0


@pytest.mark.parametrize(
    ("missing", "message"),
    [
        (["msvcp140.dll"], r"Visual C\+\+ 재배포 가능 패키지"),  # 설치는 됐는데 DLL이 없는 경우 → 재배포 패키지 안내
        ([], r"npm run setup:ocr"),  # 정말 설치가 안 된 경우
    ],
)
def test_paddle_import_failure_explains_the_cause(
    monkeypatch: pytest.MonkeyPatch, tmp_path: object, missing: list[str], message: str
) -> None:
    import sys

    from app.ocr import paddle, winprereq

    monkeypatch.setenv("PADDLE_PDX_CACHE_HOME", str(tmp_path))  # 엔진이 setdefault 하는 환경변수가 다른 테스트로 새지 않게
    monkeypatch.setitem(sys.modules, "paddleocr", None)  # 설치 여부와 무관하게 import 실패
    monkeypatch.setattr(winprereq, "missing_runtime_dlls", lambda: missing)
    with pytest.raises(RuntimeError, match=message):
        paddle.PaddleOcrEngine()
