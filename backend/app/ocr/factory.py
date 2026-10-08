import logging
from functools import lru_cache
from typing import Literal

from app.core.config import settings
from app.ocr.base import OcrEngine
from app.ocr.mock import MockOcrEngine
from app.ocr.schemas import OcrRawResult

logger = logging.getLogger(__name__)


class UnavailableOcrEngine(OcrEngine):
    """실제 OCR을 켜려다 실패했을 때(미설치·모델 다운로드 실패 등) 대신 쓰는 엔진.

    서버는 그대로 뜨고, 업로드도 된다. 인식만 실패로 처리되어 사용자가 직접 입력한다.
    """

    name = "unavailable"

    def __init__(self, reason: str) -> None:
        self.reason = reason

    def recognize(self, image_bytes: bytes) -> OcrRawResult:
        raise RuntimeError(f"OCR을 쓸 수 없습니다: {self.reason}")


@lru_cache(maxsize=1)
def get_ocr_engine() -> OcrEngine:
    """설정(OCR_ENGINE)에 맞는 엔진을 1개만 만들어 재사용한다. FastAPI Depends로도 쓴다.

    테스트에서는 app.dependency_overrides[get_ocr_engine] 로 바꿔 끼우면 된다.
    """
    if settings.ocr_engine == "paddle":
        try:
            # paddle이 설치되지 않은 환경에서도 앱이 뜨도록 필요할 때만 import
            from app.ocr.paddle import PaddleOcrEngine

            return PaddleOcrEngine()
        except Exception as error:
            logger.exception("실제 OCR(PaddleOCR) 준비 실패 → 업로드는 되지만 자동 인식 없이 직접 입력하게 됩니다")
            return UnavailableOcrEngine(str(error))
    return MockOcrEngine()


OcrStatus = Literal["mock", "paddle", "unavailable", "pending"]


def ocr_status() -> OcrStatus:
    """지금 쓰는 인식 방식. 엔진을 아직 안 불러왔으면 불러오지 않고 pending (상태 확인이 모델 로딩을 일으키지 않게)"""
    if settings.ocr_engine == "mock":
        return "mock"
    if get_ocr_engine.cache_info().currsize == 0:
        return "pending"
    return "paddle" if get_ocr_engine().name == "paddle" else "unavailable"
