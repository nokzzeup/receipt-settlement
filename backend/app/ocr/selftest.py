"""실제 OCR(PaddleOCR)이 이 PC에서 동작하는지 확인 — npm run setup:ocr 의 마지막 단계.

    python -m app.ocr.selftest

글자를 그린 시험 이미지를 만들어 인식시켜 본다. 처음이면 모델 파일(약 25MB)을 내려받는다.
"""

import sys
import time


def main() -> int:
    try:
        import cv2
        import numpy as np

        from app.ocr.paddle import PaddleOcrEngine
    except ImportError as error:
        print(f"[오류] OCR 패키지가 없습니다 ({error}). npm run setup:ocr 를 다시 실행하세요")
        return 1

    canvas = np.full((240, 720, 3), 255, np.uint8)
    cv2.putText(canvas, "TOTAL 12,345", (30, 95), cv2.FONT_HERSHEY_SIMPLEX, 1.7, (0, 0, 0), 3)
    cv2.putText(canvas, "2026-10-06 14:30", (30, 185), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 2)
    image = cv2.imencode(".png", canvas)[1].tobytes()

    print("OCR 엔진 준비 중... (처음이면 모델 파일 약 25MB를 내려받아서 1~2분 걸릴 수 있어요)")
    started = time.perf_counter()
    engine = PaddleOcrEngine()
    loaded = time.perf_counter() - started

    started = time.perf_counter()
    result = engine.recognize(image)
    took = time.perf_counter() - started
    texts = [line.text for line in result.lines]

    print(f"엔진 준비 {loaded:.1f}초 · 시험 이미지 인식 {took:.1f}초")
    print(f"인식 결과: {texts}")
    if any("12,345" in text or "12345" in text for text in texts):
        print("OCR 동작 확인 완료")
        return 0
    print("[오류] 시험 이미지의 글자를 읽지 못했어요. 위 결과를 복사해서 보내주세요")
    return 1


if __name__ == "__main__":
    sys.exit(main())
