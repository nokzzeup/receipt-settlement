"""PaddleOcrEngine — 실제 OCR (3단계, 담당: 김도현).

이 버전 기준으로 작성·확인함: paddlepaddle 3.3.1, paddleocr 3.7.0, paddlex 3.7.2 → backend/requirements-ocr.txt
버전을 올리면 아래 옵션 이름·결과 모양이 바뀔 수 있다 → 다시 확인하고 npm run ocr:eval 로 전후 비교할 것

설정 근거 (2026-10-08, 시험 영수증 사진, 2코어 CPU에서 직접 측정 — 실제 영수증 데이터로 다시 잴 것)
- 모델: PP-OCRv5_mobile_det(글자 위치 찾기) + korean_PP-OCRv5_mobile_rec(한국어 읽기)
  lang="korean" 기본값의 검출 모델(server_det)은 한 장 약 11초 vs mobile_det 약 3초, 찾은 글자 박스 수는 거의 같음
- enable_mkldnn=False: paddlepaddle 3.3.1의 CPU 가속(oneDNN) 경로에서 NotImplementedError
  (ConvertPirAttribute2RuntimeAttribute)로 인식이 실패함 → 끄면 정상
- 문서 방향 분류 켬: 거꾸로·옆으로 찍은 사진도 똑바로 찍은 것과 같은 결과 (추가 시간 거의 없음)
- 휜 종이 펴기(UVDoc)·글줄 방향 분류는 끔: 느리고, 영수증은 가로 글줄이라 필요 없음
- 검출 입력은 긴 변 1600px까지: 폰 원본(3000px+)을 그대로 넣으면 몇 배 느려짐
- 모델 파일(약 25MB)은 처음 쓸 때 자동으로 받아서 레포 맨 위 .tools/paddlex 에 저장 (git 제외)

결과 좌표는 방향 보정이 끝난 이미지 기준이다 (OcrRawResult 계약: 4점, 좌상 → 우상 → 우하 → 좌하)
"""

import logging
import os
import time

from app.core.config import REPO_ROOT
from app.ocr.base import OcrEngine
from app.ocr.convert import to_raw_result
from app.ocr.schemas import OcrRawResult

logger = logging.getLogger(__name__)

MODEL_CACHE_DIR = REPO_ROOT / ".tools" / "paddlex"
DETECTION_MODEL = "PP-OCRv5_mobile_det"
RECOGNITION_MODEL = "korean_PP-OCRv5_mobile_rec"
DETECTION_MAX_SIDE = 1600

# 엔진·전처리 설정이 바뀌면 이 값을 바꾼다 → 정확도 측정(npm run ocr:eval)이 저장해 둔 OCR 결과를 버리고 다시 인식
ENGINE_SIGNATURE = f"paddleocr-3.7.0/{DETECTION_MODEL}/{RECOGNITION_MODEL}/det{DETECTION_MAX_SIDE}/ori/v1"


class PaddleOcrEngine(OcrEngine):
    name = "paddle"

    def __init__(self) -> None:
        # paddlex는 import될 때 이 값을 읽는다 → import 전에 설정 (모델 저장 위치)
        os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(MODEL_CACHE_DIR))
        try:
            from paddleocr import PaddleOCR
        except ImportError as error:
            # 설치는 됐는데 Windows에 C++ 런타임이 없어서 DLL을 못 불러온 경우가 흔함 → 그 안내를 먼저
            from app.ocr.winprereq import install_hint, missing_runtime_dlls

            missing = missing_runtime_dlls()
            if missing:
                raise RuntimeError(install_hint(missing)) from error
            raise RuntimeError(f"PaddleOCR를 불러오지 못했습니다 ({error}) → npm run setup:ocr 를 실행하세요") from error

        started = time.perf_counter()
        self._ocr = PaddleOCR(
            text_detection_model_name=DETECTION_MODEL,
            text_recognition_model_name=RECOGNITION_MODEL,
            use_doc_orientation_classify=True,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            text_det_limit_type="max",
            text_det_limit_side_len=DETECTION_MAX_SIDE,
            enable_mkldnn=False,
        )
        logger.info("PaddleOCR 준비 완료 (%.1f초)", time.perf_counter() - started)

    def recognize(self, image_bytes: bytes) -> OcrRawResult:
        from app.ocr.preprocess import preprocess  # OpenCV는 OCR 패키지가 있을 때만 있음

        image = preprocess(image_bytes)
        result = self._ocr.predict(image)[0]
        return to_raw_result(self.name, result["rec_texts"], result["rec_scores"], result["rec_polys"])
