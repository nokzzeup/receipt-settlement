import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.ocr import factory


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["database"]) == ("ok", "ok")
    assert body["ocr"] in {"mock", "paddle", "unavailable", "pending"}


def test_ocr_status_does_not_load_the_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ocr_engine", "mock")
    assert factory.ocr_status() == "mock"

    monkeypatch.setattr(settings, "ocr_engine", "paddle")
    factory.get_ocr_engine.cache_clear()
    try:
        # 상태 확인만으로 무거운 모델을 불러오지 않음 → 첫 업로드 때 불러옴
        assert factory.ocr_status() == "pending"
        assert factory.get_ocr_engine.cache_info().currsize == 0
    finally:
        factory.get_ocr_engine.cache_clear()
