"""/api/v1 라우터 모음. 새 라우터 파일을 만들면 여기에 include_router 한 줄 추가."""

from fastapi import APIRouter

from app.api.v1 import auth, categories, expenses, health, orgs

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(orgs.router)
api_router.include_router(categories.router)
api_router.include_router(expenses.router)
