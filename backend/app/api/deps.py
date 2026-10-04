"""라우터에서 쓰는 공통 의존성. 사용 예: `def handler(db: DbSession): ...`

1단계에서 여기에 CurrentUser, 조직 멤버십·역할 체크 의존성을 추가한다.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.ocr import OcrEngine, get_ocr_engine

DbSession = Annotated[Session, Depends(get_db)]
OcrEngineDep = Annotated[OcrEngine, Depends(get_ocr_engine)]
