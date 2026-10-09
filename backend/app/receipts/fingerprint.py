"""사진 지문 (256비트 dHash) — 같은 사진을 다시 저장·크기 조절·메신저로 보낸 경우를 찾는다.

    작게 줄인 흑백 사진(17×16)에서 옆 칸보다 밝은지 여부를 256비트로 → 16진수 64자
    두 지문의 다른 비트 수(해밍 거리)가 작으면 같은 사진

측정 (2026-10-10, 시험 영수증 5장): 같은 사진을 화질 40%·크기 50%로 다시 저장 = 0~3비트,
EXIF 회전만 다른 사진 = 0, 서로 다른 영수증 = 47비트 이상 → 기준 12비트.
사진을 3%만 잘라도 47비트가 되므로 '다시 찍은 사진'은 못 잡는다 (그건 가게·일시·금액 비교가 맡음).
"""

import io

from PIL import Image, ImageOps

SIZE = 16  # 16×16 비교 = 256비트
SIMILAR_MAX_DISTANCE = 12


def perceptual_hash(image_bytes: bytes) -> str | None:
    """못 읽는 사진이면 None (업로드는 계속 진행)"""
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.draft("L", (SIZE * 8, SIZE * 8))  # JPEG는 작게 풀어서 빠르게
            upright = ImageOps.exif_transpose(image)  # 회전 정보만 다른 같은 사진도 같은 지문
            small = upright.convert("L").resize((SIZE + 1, SIZE), Image.Resampling.LANCZOS)
    except Exception:  # noqa: BLE001 — 깨진 파일·지원 안 하는 형식은 지문 없이
        return None
    pixels = small.tobytes()
    width = SIZE + 1
    bits = 0
    for row in range(SIZE):
        for col in range(SIZE):
            bits = (bits << 1) | (pixels[row * width + col] > pixels[row * width + col + 1])
    return f"{bits:0{SIZE * SIZE // 4}x}"


def hamming_distance(a: str, b: str) -> int:
    return (int(a, 16) ^ int(b, 16)).bit_count()
