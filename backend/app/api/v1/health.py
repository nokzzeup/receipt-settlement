from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession
from app.ocr import OcrStatus, ocr_status

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "error"]
    # 인식 방식: mock(고정 샘플) | paddle(실제 OCR) | unavailable(실제 OCR 준비 실패 → 직접 입력) | pending(첫 업로드 때 불러옴)
    ocr: OcrStatus


@router.get(
    "/health",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthResponse, "description": "DB 연결 실패"}},
)
def health(db: DbSession, response: Response) -> HealthResponse:
    """서버 + DB 연결 상태. DB에 못 붙으면 503."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="degraded", database="error", ocr=ocr_status())
    return HealthResponse(status="ok", database="ok", ocr=ocr_status())
