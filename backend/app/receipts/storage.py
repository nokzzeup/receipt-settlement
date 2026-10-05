"""영수증 원본 이미지 저장소 (로컬 파일시스템, settings.storage_path 아래).

DB(Receipt.image_path)에는 저장소 기준 상대경로만 넣는다 → 폴더를 옮겨도 설정만 바꾸면 됨.
    receipts/{조직 id}/{랜덤 32자}.jpg

이미지는 웹에 그냥 공개하지 않는다. 항상 권한 확인을 거치는 API(GET .../expenses/{id}/image)로만 내려준다.
"""

import logging
import os
import uuid
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


def _root() -> Path:
    return settings.storage_path.resolve()


def resolve(relative_path: str) -> Path:
    """상대경로 → 실제 파일 경로. 저장소 바깥을 가리키면 에러 (경로 조작 방지)"""
    root = _root()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"storage 바깥 경로: {relative_path}")
    return path


def save_receipt_image(org_id: int, data: bytes, extension: str) -> str:
    """이미지를 저장하고 상대경로를 돌려준다. 같은 폴더에 임시 파일로 쓴 뒤 이름을 바꿔서 반쯤 쓴 파일이 남지 않게"""
    relative = f"receipts/{org_id}/{uuid.uuid4().hex}.{extension}"
    path = resolve(relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes(data)
    os.replace(temp, path)
    return relative


def delete_image(relative_path: str) -> None:
    """파일 삭제. 실패해도 예외를 던지지 않는다 (DB는 이미 정리됐고, 남은 파일은 해가 없음)"""
    try:
        resolve(relative_path).unlink(missing_ok=True)
    except (OSError, ValueError):
        logger.exception("영수증 이미지 삭제 실패: %s", relative_path)
