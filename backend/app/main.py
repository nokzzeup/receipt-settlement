from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  모든 모델 등록 (relationship 문자열 참조 해석)
from app.api.v1.router import api_router
from app.core.config import settings
from app.web import mount_frontend


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# 서버 모드(npm run serve): 빌드된 화면도 같은 포트로 → 다른 PC·폰은 http://노트북IP:포트 하나로 접속
# (API 라우터를 먼저 등록해야 /api 요청이 화면 쪽으로 새지 않음)
if settings.serve_frontend:
    mount_frontend(app, settings.frontend_dist)
