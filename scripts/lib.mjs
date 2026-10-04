// npm 명령(setup·dev·start·test·db:*)이 같이 쓰는 경로·실행 도우미. Windows/Mac 차이를 여기서 흡수한다.
import { spawn, spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
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

export const APP_URL = 'http://localhost:5173'
// Vite(5173)를 거쳐 백엔드까지 확인 → 둘 다 떠 있어야 OK
const HEALTH_URL = 'http://127.0.0.1:5173/api/v1/health'

// 파이썬 출력을 UTF-8로 고정 → Windows에서도 한글 로그가 깨지지 않음
const PYTHON_ENV = { ...process.env, PYTHONUTF8: '1', PYTHONUNBUFFERED: '1' }

export function fail(message) {
  console.error(`\n[오류] ${message}\n`)
  process.exit(1)
}

// ---------------------------------------------------------------------------
// setup 상태: 패키지 목록 파일이 바뀌면(git pull 등) setup을 다시 해야 함을 알 수 있게 지문을 남긴다
const STAMP_FILE = path.join(VENV_DIR, 'setup-stamp.txt')
const STAMP_SOURCES = [
  'backend/requirements.txt',
  'backend/requirements-dev.txt',
  'package-lock.json',
  'frontend/package-lock.json',
]

function currentSetupStamp() {
  const hash = createHash('sha256')
  for (const file of STAMP_SOURCES) hash.update(readFileSync(path.join(ROOT, file)))
  return hash.digest('hex')
}

export function writeSetupStamp() {
  writeFileSync(STAMP_FILE, currentSetupStamp())
}

/** setup이 끝났고, 그 뒤로 패키지 목록이 바뀌지 않았는지 */
export function isSetupUpToDate() {
  if (!existsSync(VENV_PYTHON)) return false
  if (!existsSync(path.join(ROOT, 'node_modules')) || !existsSync(path.join(FRONTEND, 'node_modules'))) return false
  try {
    return readFileSync(STAMP_FILE, 'utf8').trim() === currentSetupStamp()
  } catch {
    return false
  }
}

export function requireVenv() {
  if (!existsSync(VENV_PYTHON)) fail('백엔드 환경이 아직 없습니다. 먼저 `npm run setup` 을 실행하세요.')
}

export function requireSetup() {
  requireVenv()
  if (!existsSync(path.join(ROOT, 'node_modules')) || !existsSync(path.join(FRONTEND, 'node_modules'))) {
    fail('npm 패키지가 아직 없습니다. 먼저 `npm run setup` 을 실행하세요.')
  }
  if (!isSetupUpToDate()) {
    console.warn('\n[주의] 설치 이후 패키지 목록이 바뀌었습니다 (git pull 등). 에러가 나면 `npm run setup` 을 다시 실행하세요.\n')
  }
}

// ---------------------------------------------------------------------------
/** 명령을 실행하고 끝날 때까지 기다린다. 실패하면 그 종료 코드로 같이 종료 */
export function run(command, args, options = {}) {
  const result = spawnSync(command, args, { stdio: 'inherit', ...options })
  if (result.error) fail(`${command} 실행 실패: ${result.error.message}`)
  if (result.status !== 0) process.exit(result.status ?? 1)
}

/**
 * 오래 도는 프로세스(개발 서버) 실행. Ctrl+C는 자식이 직접 받아서 정리하고,
 * 자식이 끝나면 같은 종료 코드로 끝난다. onExit를 주면 종료 코드 처리를 맡긴다.
 */
export function runForeground(command, args, options = {}, onExit) {
  const child = spawn(command, args, { stdio: 'inherit', ...options })
  child.on('error', (error) => fail(`${command} 실행 실패: ${error.message}`))
  process.on('SIGINT', () => {}) // Ctrl+C는 터미널이 자식에게도 보내므로 여기선 무시하고 자식 종료를 기다림
  process.on('SIGTERM', () => child.kill('SIGTERM'))
  child.on('exit', (code, signal) => {
    const exitCode = code ?? (signal ? 1 : 0)
    if (onExit) onExit(exitCode)
    else process.exit(exitCode)
  })
  return child
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

// ---------------------------------------------------------------------------
/** 백엔드·프론트가 둘 다 응답하는지 */
export async function isAppRunning() {
  try {
    const response = await fetch(HEALTH_URL, { signal: AbortSignal.timeout(1500) })
    return response.ok
  } catch {
    return false
  }
}

/** 기본 브라우저로 열기. 실패해도(브라우저 없는 환경 등) 주소만 안내하고 넘어간다 */
export function openBrowser(url) {
  const [command, args, extra] = isWindows
    ? ['cmd.exe', ['/d', '/s', '/c', `start "" "${url}"`], { windowsVerbatimArguments: true }]
    : process.platform === 'darwin'
      ? ['open', [url], {}]
      : ['xdg-open', [url], {}]
  const child = spawn(command, args, { stdio: 'ignore', detached: true, ...extra })
  child.on('error', () => console.log(`브라우저를 자동으로 못 열었어요 → 직접 여세요: ${url}`))
  child.unref()
}
