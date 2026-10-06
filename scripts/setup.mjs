// npm run setup — 처음 한 번 (git pull로 패키지가 바뀐 뒤에도 다시 실행)
// .env 생성 → 파이썬 가상환경 + 백엔드 패키지 → DB 생성 → npm 패키지
import { spawnSync } from 'node:child_process'
import { copyFileSync, existsSync, rmSync } from 'node:fs'
import path from 'node:path'
import {
  DEV_PORTS,
  FRONTEND,
  ROOT,
  SERVER_PORTS,
  VENV_DIR,
  VENV_PYTHON,
  ensurePortsFree,
  fail,
  isWindows,
  run,
  runNpm,
  runPython,
  writeSetupStamp,
} from './lib.mjs'

// 3.14 이상: 3단계 PaddleOCR(paddlepaddle)가 아직 지원 안 함 / 3.15: pydantic도 미지원
const SUPPORTED_PYTHON = ['3.13', '3.12']

let stepNo = 0
function step(title) {
  console.log(`\n[${++stepNo}/5] ${title}`)
}

function pythonVersion(command, args = []) {
  const result = spawnSync(command, [...args, '-c', 'import sys; print("%d.%d" % sys.version_info[:2])'], {
    encoding: 'utf8',
  })
  if (result.error || result.status !== 0) return null
  return result.stdout.trim()
}

function findPython() {
  const candidates = isWindows
    ? [['py', ['-3.13']], ['py', ['-3.12']], ['python', []], ['python3', []]]
    : [['python3.13', []], ['python3.12', []], ['python3', []], ['python', []]]
  const unsupported = new Set()
  for (const [command, args] of candidates) {
    const version = pythonVersion(command, args)
    if (!version) continue
    if (SUPPORTED_PYTHON.includes(version)) return { command, args, version }
    unsupported.add(version)
  }
  const found = unsupported.size ? `찾은 버전: ${[...unsupported].join(', ')} → ` : ''
  fail(
    `Python 3.13(또는 3.12)이 필요합니다. ${found}python.org에서 3.13을 설치한 뒤 터미널을 새로 열고 다시 실행하세요.\n` +
      '        (3.14 이상은 3단계에서 쓸 PaddleOCR가 아직 지원하지 않습니다)',
  )
}

// ---------------------------------------------------------------------------
step('Node.js 버전 확인')
const [major, minor] = process.versions.node.split('.').map(Number)
if (major < 22 || (major === 22 && minor < 22)) {
  fail(`Node.js ${process.versions.node} → 22.22 이상이 필요합니다 (nodejs.org에서 24 LTS 설치)`)
}
console.log(`Node.js ${process.versions.node} OK`)
// 서버가 켜진 채로 설치하면 Windows에선 사용 중인 파일을 못 지워서 npm ci·pip가 중간에 실패함 → 먼저 확인
// (공용 서버도 같은 파이썬 환경을 쓰므로 같이 확인)
await ensurePortsFree([...DEV_PORTS, ...SERVER_PORTS])

// ---------------------------------------------------------------------------
step('.env 준비')
const envFile = path.join(ROOT, '.env')
if (existsSync(envFile)) {
  console.log('.env 이미 있음 → 그대로 사용')
} else {
  copyFileSync(path.join(ROOT, '.env.example'), envFile)
  console.log('.env.example → .env 복사')
}

// ---------------------------------------------------------------------------
step('백엔드: 파이썬 가상환경 + 패키지 설치')
if (existsSync(VENV_PYTHON)) {
  const venvVersion = pythonVersion(VENV_PYTHON)
  if (!SUPPORTED_PYTHON.includes(venvVersion)) {
    console.log(`기존 가상환경(Python ${venvVersion ?? '알 수 없음'})은 지원 버전이 아니라서 새로 만듭니다`)
    try {
      rmSync(VENV_DIR, { recursive: true, force: true })
    } catch (error) {
      fail(`backend/.venv 를 지울 수 없습니다 (${error.code}). VS Code·터미널 등 이 폴더를 쓰는 프로그램을 닫고 다시 실행하세요.`)
    }
  }
}
if (!existsSync(VENV_PYTHON)) {
  const python = findPython()
  console.log(`Python ${python.version} 로 backend/.venv 생성`)
  run(python.command, [...python.args, '-m', 'venv', VENV_DIR])
}
runPython(['-m', 'pip', 'install', '--disable-pip-version-check', '-q', '-r', 'requirements-dev.txt'])
console.log('백엔드 패키지 설치 완료')

// ---------------------------------------------------------------------------
step('DB 생성/업데이트 (backend/data/app.db)')
runPython(['-m', 'alembic', 'upgrade', 'head'])

// ---------------------------------------------------------------------------
step('npm 패키지 설치 (루트 + frontend)')
runNpm(['ci', '--no-audit', '--no-fund'], ROOT)
runNpm(['ci', '--no-audit', '--no-fund'], FRONTEND)

writeSetupStamp() // 패키지 목록이 다시 바뀌기 전까지 더블클릭 실행이 setup을 건너뜀
if (process.env.SETUP_CALLED_BY_LAUNCHER) {
  console.log('\n준비 완료! 이어서 실행합니다.\n') // 더블클릭 실행 파일이 setup을 부른 경우
} else {
  console.log('\n준비 완료! 이제 start 파일 더블클릭(또는 `npm run dev`)으로 실행하세요.')
  console.log('팀 공용 서버로 켜려면 server 파일 더블클릭(또는 `npm run serve`).\n')
}
