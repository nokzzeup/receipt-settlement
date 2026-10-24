# scripts

## 실행 스크립트 (건드릴 일 거의 없음)
루트의 `npm run ...` 명령이 부르는 파일들. Windows/Mac 경로 차이를 여기서 처리한다.

| 파일 | 하는 일 |
|---|---|
| `start.mjs` | 더블클릭 실행(`start-windows.bat`/`start-mac.command`)의 첫 화면 — 1) 개인 로컬 / 2) 팀 공용 서버를 묻고 아래 둘 중 하나 실행 |
| `launch.mjs` | 개인 로컬 (메뉴 1번, `npm start`) — 필요하면 setup → dev → 브라우저 열기 |
| `serve.mjs` | 팀 공용 서버 (메뉴 2번, `npm run serve`) — 화면 빌드 → DB 백업·업데이트 → 0.0.0.0:8080 + 외부 접속 주소 |
| `tailscale.mjs` | 외부 접속 고정 주소 (Tailscale Funnel) — 서버 PC에 Tailscale이 있을 때 |
| `tunnel.mjs` | 외부 접속 임시 주소 (Cloudflare Quick Tunnel) — Tailscale이 없을 때, 켤 때마다 바뀜 |
| `setup.mjs` | `npm run setup` — .env, 파이썬 가상환경·패키지, DB 생성, npm 패키지 |
| `dev.mjs` | `npm run dev` — 아래 두 개를 터미널 하나에서 같이 실행 |
| `backend.mjs` | 마이그레이션 적용 후 FastAPI 실행 (자동 재시작) |
| `frontend.mjs` | Vite 개발 서버 |
| `py.mjs` | `backend/.venv` 파이썬으로 명령 실행 (`npm test`, `npm run db:*`) |
| `lib.mjs` | 위 파일들이 같이 쓰는 도우미 |

## 유틸 (7단계 정확도 측정 등)
`dataset/` 정답 라벨과 OCR+파싱 결과를 비교하는 파이썬 스크립트는 여기에 둔다.
백엔드 코드(`app.ocr`, `app.parsing` 등)를 쓰려면 스크립트 맨 위에 아래 두 줄을 넣고, 백엔드 가상환경 파이썬으로 실행한다.

```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))
```

```bash
# Windows
backend\.venv\Scripts\python scripts\측정스크립트.py
# Mac
backend/.venv/bin/python scripts/측정스크립트.py
```
