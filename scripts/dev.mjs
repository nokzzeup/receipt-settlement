// npm run dev — 백엔드(FastAPI) + 프론트(Vite)를 터미널 하나에서 같이 실행. Ctrl+C 한 번이면 둘 다 종료
// npm run dev:host — 같은 와이파이의 폰에서도 접속 가능하게 실행
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { ROOT, requireSetup, runForeground } from './lib.mjs'

requireSetup()

const host = process.argv.includes('--host')
const pkgDir = path.join(ROOT, 'node_modules', 'concurrently')
const { bin } = JSON.parse(readFileSync(path.join(pkgDir, 'package.json'), 'utf8'))
const concurrently = path.join(pkgDir, typeof bin === 'string' ? bin : bin.concurrently)

runForeground(
  process.execPath,
  [
    concurrently,
    '--names', 'api,web',
    '--prefix-colors', 'cyan,green',
    '--kill-others-on-fail', // 한쪽이 에러로 죽으면 다른 쪽도 종료 → 에러를 놓치지 않게
    'node scripts/backend.mjs',
    `node scripts/frontend.mjs${host ? ' --host' : ''}`,
  ],
  { cwd: ROOT },
)
