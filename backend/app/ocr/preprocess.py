"""OCR 전처리 (OpenCV, 담당: 김도현). OCR 패키지(requirements-ocr.txt)가 있을 때만 쓰인다.

지금 하는 것 — 시험 영수증으로 확인한 최소한
1. 디코딩 + EXIF 회전 적용: 폰 사진은 픽셀은 누워 있고 회전 정보(EXIF)만 붙어 있는 경우가 많다.
   OpenCV 4.10(paddlex가 고정)의 imdecode(IMREAD_COLOR)가 EXIF 회전을 적용하는 것을 확인함 (2026-10-08)
2. 너무 큰 사진은 긴 변 3200px로 축소 (메모리·속도. 글자 인식에는 충분)
거꾸로(180°)·옆으로 찍은 사진은 PaddleOCR의 문서 방향 분류 모델이 바로잡는다 (paddle.py)

더 넣을 후보 — 실제 영수증 데이터로 효과를 재 보고 추가할 것 (npm run ocr:eval 로 전후 비교)
- 대비 보정(CLAHE): 바랜 감열지
- 그림자·조명 차이 보정
- 영수증 영역만 잘라내기 + 원근 보정: 책상이 넓게 찍힌 사진
- 휜 종이 펴기: PaddleOCR의 UVDoc (느림)
"""

import cv2
import numpy as np

MAX_SIDE = 3200


def decode_image(data: bytes) -> np.ndarray:
    """바이트 → BGR 이미지 (EXIF 회전 적용됨). 읽을 수 없으면 ValueError"""
    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("이미지를 읽을 수 없습니다 (손상됐거나 지원하지 않는 형식)")
    return image


def limit_size(image: np.ndarray, max_side: int = MAX_SIDE) -> np.ndarray:
    height, width = image.shape[:2]
    scale = max_side / max(height, width)
    if scale >= 1:
        return image
    return cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)


def preprocess(data: bytes) -> np.ndarray:
    return limit_size(decode_image(data))
