// npm 명령(setup·dev·test·db:*)이 같이 쓰는 경로·실행 도우미. Windows/Mac 차이를 여기서 흡수한다.
import { spawn, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

export const isWindows = process.platform === 'win32'
export const ROOT = fileURLToPath(new URL('..', import.meta.url))
export const BACKEND = path.join(ROOT, 'backend')
export const FRONTEND = path.join(ROOT, 'frontend')
export const VENV_DIR = path.join(BACKEND, '.venv')
export const VENV_PYTHON = isWindows
  ? path.join(VENV_DIR, 'Scripts', 'python.exe')
  : path.join(VENV_DIR, 'bin', 'python')

// 파이썬 출력을 UTF-8로 고정 → Windows에서도 한글 로그가 깨지지 않음
const PYTHON_ENV = { ...process.env, PYTHONUTF8: '1', PYTHONUNBUFFERED: '1' }

export function fail(message) {
  console.error(`\n[오류] ${message}\n`)
  process.exit(1)
}

export function requireVenv() {
  if (!existsSync(VENV_PYTHON)) fail('백엔드 환경이 아직 없습니다. 먼저 `npm run setup` 을 실행하세요.')
}

export function requireSetup() {
  requireVenv()
  if (!existsSync(path.join(ROOT, 'node_modules')) || !existsSync(path.join(FRONTEND, 'node_modules'))) {
    fail('npm 패키지가 아직 없습니다. 먼저 `npm run setup` 을 실행하세요.')
  }
}

/** 명령을 실행하고 끝날 때까지 기다린다. 실패하면 그 종료 코드로 같이 종료 */
export function run(command, args, options = {}) {
  const result = spawnSync(command, args, { stdio: 'inherit', ...options })
  if (result.error) fail(`${command} 실행 실패: ${result.error.message}`)
  if (result.status !== 0) process.exit(result.status ?? 1)
}

/**
 * 오래 도는 프로세스(개발 서버) 실행. Ctrl+C는 자식이 직접 받아서 정리하고,
 * 자식이 끝나면 같은 종료 코드로 끝난다.
 */
export function runForeground(command, args, options = {}) {
  const child = spawn(command, args, { stdio: 'inherit', ...options })
  child.on('error', (error) => fail(`${command} 실행 실패: ${error.message}`))
  process.on('SIGINT', () => {}) // Ctrl+C는 터미널이 자식에게도 보내므로 여기선 무시하고 자식 종료를 기다림
  process.on('SIGTERM', () => child.kill('SIGTERM'))
  child.on('exit', (code, signal) => process.exit(code ?? (signal ? 1 : 0)))
}

export function runPython(args) {
  run(VENV_PYTHON, args, { cwd: BACKEND, env: PYTHON_ENV })
}

export function runPythonForeground(args) {
  runForeground(VENV_PYTHON, args, { cwd: BACKEND, env: PYTHON_ENV })
}

/** npm 실행. `npm run ...`으로 불렸으면 같은 npm을 node로 직접 실행(Windows .cmd 문제 회피) */
export function runNpm(args, cwd) {
  const npmCli = process.env.npm_execpath
  if (npmCli && npmCli.endsWith('.js')) {
    run(process.execPath, [npmCli, ...args], { cwd })
  } else if (isWindows) {
    run(`npm ${args.join(' ')}`, undefined, { cwd, shell: true })
  } else {
    run('npm', args, { cwd })
  }
}
