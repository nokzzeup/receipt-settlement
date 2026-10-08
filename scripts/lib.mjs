// npm 명령(setup·dev·start·test·db:*)이 같이 쓰는 경로·실행 도우미. Windows/Mac 차이를 여기서 흡수한다.
import { spawn, spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import net from 'node:net'
import os from 'node:os'
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

// 프론트는 IPv4(127.0.0.1)에 고정 (vite.config.ts). localhost는 Windows에서 IPv6(::1)로 풀려서 OS마다 동작이 달라짐
export const APP_URL = 'http://127.0.0.1:5173'
// Vite(5173)를 거쳐 백엔드까지 확인 → 둘 다 떠 있어야 OK.
// IPv6 주소도 보는 이유: 이전 버전(localhost 사용)으로 켜둔 서버가 Windows에선 ::1에 떠 있음
const HEALTH_URLS = ['http://127.0.0.1:5173/api/v1/health', 'http://[::1]:5173/api/v1/health']
export const DEV_PORTS = [
  { host: '127.0.0.1', port: 8000, label: '백엔드' },
  { host: '127.0.0.1', port: 5173, label: '프론트' },
  { host: '::1', port: 5173, label: '프론트' },
]

// ---------------------------------------------------------------------------
// 공용 서버 모드 (npm run serve, server-*.bat): 화면 + API를 포트 하나로, 같은 와이파이의 다른 기기에서도 접속
// 개발 서버(8000·5173)와 포트·데이터가 달라서 둘을 동시에 켜도 된다
export const SERVER_DATA_DIR = path.join(ROOT, 'server-data') // 운영 DB·영수증 사진·로그인 키
export const SERVER_PORT = Number(readEnvValue('SERVER_PORT')) || 8080
export const SERVER_PORTS = [{ host: '0.0.0.0', port: SERVER_PORT, label: '공용 서버' }]

// 파이썬 출력을 UTF-8로 고정 → Windows에서도 한글 로그가 깨지지 않음
const PYTHON_ENV = { ...process.env, PYTHONUTF8: '1', PYTHONUNBUFFERED: '1' }

/** 환경변수 → 없으면 레포 루트 .env 에서 KEY=값 을 읽는다 (Node 스크립트용 간단 버전) */
export function readEnvValue(key) {
  if (process.env[key]) return process.env[key]
  try {
    for (const line of readFileSync(path.join(ROOT, '.env'), 'utf8').split(/\r?\n/)) {
      const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/)
      if (match && match[1] === key) return match[2].replace(/^(['"])(.*)\1$/, '$2')
    }
  } catch {
    // .env 가 없으면 기본값
  }
  return undefined
}

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

// 실제 OCR(PaddleOCR) 설치 상태 — npm run setup:ocr 가 남기는 지문. requirements-ocr.txt 가 바뀌면 다시 설치
const OCR_REQUIREMENTS = path.join(BACKEND, 'requirements-ocr.txt')
const OCR_STAMP_FILE = path.join(VENV_DIR, 'ocr-stamp.txt')

function currentOcrStamp() {
  return createHash('sha256').update(readFileSync(OCR_REQUIREMENTS)).digest('hex')
}

export function writeOcrStamp() {
  writeFileSync(OCR_STAMP_FILE, currentOcrStamp())
}

/** .env 의 OCR_ENGINE (mock | paddle) */
export function ocrEngineSetting() {
  return (readEnvValue('OCR_ENGINE') ?? 'mock').trim().toLowerCase()
}

/** 실제 OCR을 쓰기로 했는데(OCR_ENGINE=paddle) 설치가 안 됐거나 버전 목록이 바뀌었는지 */
export function isOcrSetupNeeded() {
  if (ocrEngineSetting() !== 'paddle') return false
  try {
    return readFileSync(OCR_STAMP_FILE, 'utf8').trim() !== currentOcrStamp()
  } catch {
    return true
  }
}

/** 실행 창 맨 위에 찍는 한 줄: 코드 버전 + .env 의 OCR 설정 → 캡처 한 장으로 어떤 상태인지 알 수 있게 */
export function startupSummary() {
  const setting = ocrEngineSetting()
  const label = { paddle: 'paddle(실제 OCR)', mock: 'mock(가짜, 고정 샘플)' }[setting] ?? `${setting} ← mock 또는 paddle만 가능`
  return `    코드 버전: ${codeVersion() ?? '알 수 없음'} · 인식(OCR) 설정: ${label}`
}

// 실행 창에 인식(OCR) 상태를 항상 한 줄 보여준다 — 안 보이면 왜 인식이 안 되는지 알 수 없음
const OCR_STATUS_TEXT = {
  paddle: '실제 OCR(PaddleOCR) 사용 중 — 한 장에 몇 초 걸려요',
  pending: '실제 OCR(PaddleOCR) — 첫 업로드 때 모델을 불러와서 첫 장만 10~30초 더 걸려요',
  mock: '가짜(Mock) — 사진과 상관없이 고정 샘플("행복마트 테스트점")이 채워져요 → 실제 OCR은 서버를 끄고 npm run setup:ocr',
  unavailable: '[실패] 실제 OCR을 켜지 못했어요 (위쪽 Traceback 참고) — 업로드는 되고, 내용은 직접 입력',
}

/** 실행 중인 백엔드(/api/v1/health)에 OCR 상태를 물어본다 → { ocr: paddle|pending|mock|unavailable|null, text } */
export async function checkOcrStatus(baseUrl) {
  let ocr = null
  try {
    const response = await fetch(`${baseUrl}/api/v1/health`, { signal: AbortSignal.timeout(5000) })
    const body = await response.json()
    if (Object.hasOwn(OCR_STATUS_TEXT, body.ocr)) ocr = body.ocr
  } catch {
    // 응답 없음·예전 버전 → 아래 안내
  }
  const text = ocr
    ? OCR_STATUS_TEXT[ocr]
    : `확인 못 했어요 → 브라우저에서 ${baseUrl}/api/v1/health 를 열어 "ocr" 값 확인 ("ocr"이 없으면 예전 버전 코드)`
  return { ocr, text }
}

/** 이 폴더 코드의 커밋 번호(앞 7자리). git 프로그램 없이 .git 폴더를 직접 읽는다. 모르면 null */
export function codeVersion() {
  try {
    const gitDir = path.join(ROOT, '.git')
    const head = readFileSync(path.join(gitDir, 'HEAD'), 'utf8').trim()
    if (!head.startsWith('ref: ')) return head.slice(0, 7) // 특정 커밋으로 이동해 둔 상태(detached)
    const ref = head.slice('ref: '.length)
    const looseRef = path.join(gitDir, ...ref.split('/'))
    if (existsSync(looseRef)) return readFileSync(looseRef, 'utf8').trim().slice(0, 7)
    // clone 직후 등: 브랜치 위치가 packed-refs 한 파일에 모여 있음
    const packed = readFileSync(path.join(gitDir, 'packed-refs'), 'utf8')
    const line = packed.split(/\r?\n/).find((entry) => entry.endsWith(` ${ref}`))
    return line ? line.slice(0, 7) : null
  } catch {
    return null
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

/** extraEnv: 이 실행에만 덮어쓸 환경변수 (서버 모드의 DATA_DIR 등) */
export function runPython(args, extraEnv = {}) {
  run(VENV_PYTHON, args, { cwd: BACKEND, env: { ...PYTHON_ENV, ...extraEnv } })
}

export function runPythonForeground(args, extraEnv = {}, onExit) {
  return runForeground(VENV_PYTHON, args, { cwd: BACKEND, env: { ...PYTHON_ENV, ...extraEnv } }, onExit)
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
  const results = await Promise.all(
    HEALTH_URLS.map(async (url) => {
      try {
        const response = await fetch(url, { signal: AbortSignal.timeout(1500) })
        return response.ok
      } catch {
        return false
      }
    }),
  )
  return results.some(Boolean)
}

/** 포트를 잠깐 열어보고 결과 코드를 돌려준다 (null = 사용 가능) */
function probePort(host, port) {
  return new Promise((resolve) => {
    const server = net.createServer()
    server.once('error', (error) => resolve(error.code ?? 'ERROR'))
    server.listen({ host, port }, () => server.close(() => resolve(null)))
  })
}

/** 공용 서버가 이 PC에서 이미 돌고 있는지 */
export async function isServerRunning(port = SERVER_PORT) {
  try {
    const response = await fetch(`http://127.0.0.1:${port}/api/v1/health`, { signal: AbortSignal.timeout(1500) })
    return response.ok
  } catch {
    return false
  }
}

/**
 * 같은 와이파이의 다른 기기가 이 PC에 들어올 때 쓸 주소(IPv4) 목록.
 * WSL·Hyper-V·VirtualBox 같은 가상 어댑터 주소는 다른 기기에서 못 들어오므로 실제 어댑터가 있으면 뺀다
 */
export function lanAddresses() {
  const all = []
  for (const [name, infos] of Object.entries(os.networkInterfaces())) {
    for (const info of infos ?? []) {
      if (info.family !== 'IPv4' || info.internal || info.address.startsWith('169.254.')) continue
      all.push({ name, address: info.address })
    }
  }
  const virtual = /vEthernet|WSL|Hyper-V|VirtualBox|VMware|docker|^br-|^veth|vboxnet|utun|Loopback/i
  const real = all.filter((entry) => !virtual.test(entry.name))
  return real.length ? real : all
}

/**
 * 서버를 띄우거나 설치(npm ci)하기 전에 포트 확인. 문제가 있으면 이유를 설명하고 종료한다.
 * (Windows는 실행 중인 서버의 파일을 지울 수 없어서, 켜진 채로 설치하면 중간에 실패함)
 */
export async function ensurePortsFree(ports = DEV_PORTS) {
  const inUse = new Set()
  const reserved = new Set()
  for (const { host, port, label } of ports) {
    const code = await probePort(host, port)
    if (code === 'EADDRINUSE') inUse.add(`${port}(${label})`)
    else if (code === 'EACCES') reserved.add(`${port}(${label})`)
    // 그 외(EADDRNOTAVAIL, EAFNOSUPPORT 등)는 그 주소가 없는 PC(IPv6 꺼짐 등)라서 무시
  }
  if (!inUse.size && !reserved.size) return

  const lines = []
  if (inUse.size) {
    lines.push(
      `포트 ${[...inUse].join(', ')}를 이미 다른 프로그램이 쓰고 있어요.`,
      '→ 다른 창에 서버(start·server 파일, npm run dev·serve)가 켜져 있으면 그 창을 닫고 다시 실행하세요.',
      '→ 켜둔 창이 없는데도 그러면 PC를 재시작해 보세요.',
    )
  }
  if (reserved.size) {
    lines.push(
      `Windows가 포트 ${[...reserved].join(', ')}를 예약해둬서 쓸 수 없어요 (Docker·WSL을 설치하면 생기는 문제).`,
      '→ 관리자 권한 PowerShell에서 아래 두 줄 실행 후 다시 시도:',
      '     net stop winnat',
      '     net start winnat',
    )
  }
  fail(lines.join('\n        '))
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
