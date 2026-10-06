"""서버 모드에서 빌드된 화면(frontend/dist)을 API와 같은 포트로 내보낸다.

개발할 땐 Vite 개발 서버(5173)가 화면을 띄우고 /api만 백엔드로 넘기지만, 공용 서버로 돌릴 땐
화면을 미리 빌드해 두고 백엔드 하나가 둘 다 내보낸다 → 다른 PC·폰은 주소 하나(http://노트북IP:8080)만 알면 됨

- /api/... : API (없는 주소면 404 — 화면으로 대체하지 않음)
- 실제 파일이 있으면 그 파일 (아이콘, manifest, sw.js 등). /assets/ 는 이름에 해시가 붙은 빌드 결과물
- 나머지 주소(/orgs/3/expenses 등)는 전부 index.html → 화면 이동은 프론트 라우터가 처리 (SPA)
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# 다시 빌드하면 바로 반영돼야 하는 파일 → 브라우저가 매번 확인하게 (나머지는 이름에 해시가 있어서 캐시 OK)
_NO_CACHE = {"index.html", "sw.js", "registerSW.js", "manifest.webmanifest"}


def mount_frontend(app: FastAPI, dist: Path) -> None:
    dist = dist.resolve()
    index = dist / "index.html"
    if not index.is_file():
        raise RuntimeError(f"빌드된 화면이 없습니다: {index} → frontend에서 vite build를 먼저 실행하세요")

    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(404, "Not Found")
        file = (dist / path).resolve()
        if path and file.is_file() and file.is_relative_to(dist):  # dist 바깥 파일은 절대 안 내보냄
            headers = {"Cache-Control": "no-cache"} if file.name in _NO_CACHE else None
            return FileResponse(file, headers=headers)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
