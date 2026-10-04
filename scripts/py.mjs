// backend/.venv 의 파이썬으로 명령 실행 (npm test, npm run db:*). 예: node scripts/py.mjs -m pytest
import { requireVenv, runPython } from './lib.mjs'

requireVenv()
runPython(process.argv.slice(2))
