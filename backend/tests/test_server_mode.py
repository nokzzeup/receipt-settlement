"""공용 서버 모드: 화면 같이 내보내기, 운영 데이터 폴더 분리, DB 백업"""

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import BACKEND_DIR, Settings
from app.ops.backup import backup_sqlite
from app.web import mount_frontend


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    """빌드 결과(frontend/dist) 흉내"""
    root = tmp_path / "dist"
    (root / "assets").mkdir(parents=True)
    (root / "index.html").write_text("<html>app</html>", encoding="utf-8")
    (root / "assets" / "index-abc123.js").write_text("console.log(1)", encoding="utf-8")
    (root / "sw.js").write_text("// sw", encoding="utf-8")
    (root / "pwa-192x192.png").write_bytes(b"\x89PNG")
    (tmp_path / "secret.txt").write_text("dist 바깥 파일", encoding="utf-8")
    return root


@pytest.fixture
def web(dist: Path) -> TestClient:
    app = FastAPI()

    @app.get("/api/v1/ping")
    def ping() -> dict[str, str]:
        return {"pong": "ok"}

    mount_frontend(app, dist)  # 실제 앱처럼 API 라우터를 먼저 등록한 뒤에
    return TestClient(app)


def test_api_routes_win_over_frontend(web: TestClient) -> None:
    assert web.get("/api/v1/ping").json() == {"pong": "ok"}
    # 없는 API 주소는 화면(index.html)이 아니라 404
    assert web.get("/api/v1/nothing").status_code == 404
    assert web.get("/api").status_code == 404


def test_files_and_spa_fallback(web: TestClient) -> None:
    home = web.get("/")
    assert home.text == "<html>app</html>"
    assert home.headers["cache-control"] == "no-cache"

    # 화면 주소로 바로 들어오거나 새로고침해도 index.html → 프론트 라우터가 처리
    deep = web.get("/orgs/3/expenses/12")
    assert deep.status_code == 200
    assert deep.text == "<html>app</html>"

    assert web.get("/assets/index-abc123.js").text == "console.log(1)"
    assert web.get("/sw.js").headers["cache-control"] == "no-cache"
    assert web.get("/pwa-192x192.png").content == b"\x89PNG"


def test_files_outside_dist_are_never_served(web: TestClient) -> None:
    for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"):
        assert "바깥" not in web.get(path).text


def test_mount_requires_build(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="빌드된 화면이 없습니다"):
        mount_frontend(FastAPI(), tmp_path / "missing")


def test_data_dir_moves_db_and_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATA_DIR", raising=False)

    default = Settings(_env_file=None)
    assert default.data_path == BACKEND_DIR / "data"
    assert default.database_url == f"sqlite:///{(BACKEND_DIR / 'data' / 'app.db').as_posix()}"

    server = Settings(_env_file=None, data_dir=tmp_path / "server-data")
    assert server.database_url == f"sqlite:///{(tmp_path / 'server-data' / 'app.db').as_posix()}"

    explicit = Settings(_env_file=None, data_dir=tmp_path, database_url="postgresql+psycopg://u:p@h/db")
    assert explicit.database_url == "postgresql+psycopg://u:p@h/db"  # 직접 지정하면 그대로


def test_backup_copies_db_and_keeps_latest(tmp_path: Path) -> None:
    db_file = tmp_path / "app.db"
    backups = tmp_path / "backups"
    assert backup_sqlite(db_file, backups) is None  # 첫 실행: DB 없음

    with closing(sqlite3.connect(db_file)) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("CREATE TABLE t (v INTEGER)")
        conn.execute("INSERT INTO t VALUES (42)")
        conn.commit()
        # 연결을 연 채로(서버가 켜져 있는 상황) 백업해도 WAL에 있는 내용까지 들어감
        target = backup_sqlite(db_file, backups)
    assert target is not None
    with closing(sqlite3.connect(target)) as copy:
        assert copy.execute("SELECT v FROM t").fetchall() == [(42,)]

    for i in range(12):
        (backups / f"app-20200101-0000{i:02d}.db").write_bytes(b"old")
    backup_sqlite(db_file, backups, keep=3)
    kept = sorted(p.name for p in backups.glob("app-*.db"))
    assert len(kept) == 3
    assert not any(name.startswith("app-2020") for name in kept[-1:])  # 가장 최근 것이 남음
