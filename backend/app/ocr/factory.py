from functools import lru_cache

from app.core.config import settings
from app.ocr.base import OcrEngine
from app.ocr.mock import MockOcrEngine


@lru_cache(maxsize=1)
def get_ocr_engine() -> OcrEngine:
    """설정(OCR_ENGINE)에 맞는 엔진을 1개만 만들어 재사용한다. FastAPI Depends로도 쓴다.

    테스트에서는 app.dependency_overrides[get_ocr_engine] 로 바꿔 끼우면 된다.
    """
    if settings.ocr_engine == "paddle":
        # paddle이 설치되지 않은 환경에서도 앱이 뜨도록 필요할 때만 import
        from app.ocr.paddle import PaddleOcrEngine

        return PaddleOcrEngine()
    return MockOcrEngine()
