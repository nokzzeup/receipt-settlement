// 프론트 개발 서버 (npm run dev가 실행). --host 를 붙이면 같은 와이파이의 폰에서도 접속 가능
import path from 'node:path'
import { FRONTEND, runForeground } from './lib.mjs'

const vite = path.join(FRONTEND, 'node_modules', 'vite', 'bin', 'vite.js')
runForeground(process.execPath, [vite, ...process.argv.slice(2)], { cwd: FRONTEND })
