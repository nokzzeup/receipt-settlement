"""PaddleOcrEngine — 3단계(김도현) 구현 예정.

구현 메모
- PaddleOCR는 버전별 API 차이가 크다 → 설치한 버전(`pip show paddleocr`)을 팀에 공유하고 그 버전 문서 기준으로 작성
- 결과는 반드시 OcrRawResult 계약으로 변환 (bbox 4점 순서: 좌상 → 우상 → 우하 → 좌하, confidence 0~1)
- 모델 로딩은 무거우므로 __init__에서 1번만 (get_ocr_engine()이 인스턴스를 재사용함)
- OpenCV 전처리(회전 보정·이진화 등)는 별도 모듈로 분리해서 여기서 호출
- paddle 패키지는 requirements.txt에 아직 없음 (OCR 안 하는 팀원은 mock으로 충분하므로 설치 부담을 안 줌)
  2026-10-04 확인: paddlepaddle 3.3.1 / paddleocr 3.7.0은 Windows·Mac(Apple Silicon)용 Python 3.12·3.13 설치 파일이
  있고 3.14용은 없음 → 팀 파이썬을 3.12/3.13으로 고정한 이유. 실제 설치할 때 버전을 다시 확인할 것
"""

from app.ocr.base import OcrEngine
from app.ocr.schemas import OcrRawResult


class PaddleOcrEngine(OcrEngine):
    name = "paddle"

    def __init__(self) -> None:
        raise NotImplementedError("PaddleOcrEngine은 3단계에서 구현합니다. 지금은 OCR_ENGINE=mock 을 쓰세요.")

    def recognize(self, image_bytes: bytes) -> OcrRawResult:
        raise NotImplementedError
