// 백엔드 개발 서버 (npm run dev가 실행). DB를 최신 구조로 맞춘 뒤 FastAPI를 코드 저장 시 자동 재시작 모드로 띄운다
import { requireVenv, runPython, runPythonForeground } from './lib.mjs'

requireVenv()
runPython(['-m', 'alembic', 'upgrade', 'head'])
runPythonForeground(['-m', 'uvicorn', 'app.main:app', '--reload', '--reload-dir', 'app', '--port', '8000'])
