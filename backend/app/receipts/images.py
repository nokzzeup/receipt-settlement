"""업로드 이미지 형식 판별. 파일 이름·Content-Type은 믿지 않고 파일 앞부분(매직 바이트)으로 판단한다."""

from dataclasses import dataclass

MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15MB (폰 사진 원본도 대부분 들어감)


@dataclass(frozen=True)
class ImageType:
    extension: str
    media_type: str


JPEG = ImageType("jpg", "image/jpeg")
PNG = ImageType("png", "image/png")
WEBP = ImageType("webp", "image/webp")

MEDIA_TYPES = {t.extension: t.media_type for t in (JPEG, PNG, WEBP)}

_HEIF_BRANDS = {b"heic", b"heix", b"hevc", b"hevx", b"heim", b"heis", b"mif1", b"msf1"}


def detect_image_type(data: bytes) -> ImageType | None:
    """지원 형식(JPG·PNG·WEBP)이면 형식을, 아니면 None"""
    if data.startswith(b"\xff\xd8\xff"):
        return JPEG
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return PNG
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return WEBP
    return None


def is_heif(data: bytes) -> bool:
    """아이폰 기본 사진 형식(HEIC). OpenCV가 못 읽어서 받지 않는다"""
    return len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in _HEIF_BRANDS
