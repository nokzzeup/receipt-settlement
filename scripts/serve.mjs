// 공용 서버 모드: 이 PC(노트북)를 팀 서버로 — server-windows.bat / server-mac.command / npm run serve
//
// 0) 맨 위에 코드 버전 + .env 의 OCR 설정을 찍는다 (창 캡처 한 장으로 상태를 알 수 있게)
// 1) 이미 켜져 있으면 접속 주소·OCR 상태만 다시 안내
// 2) 포트 확인 → 처음이거나 패키지가 바뀌었으면(git pull 등) setup부터 (OCR_ENGINE=paddle 이면 OCR 설치도)
// 3) 화면 빌드(frontend/dist) → 4) 운영 DB 자동 백업 → DB 구조 업데이트
// 5) 0.0.0.0:포트로 실행 (화면 + API를 포트 하나로) → 같은 와이파이의 다른 PC·폰이 접속할 주소 + OCR 상태 안내
//    실제 OCR이면 켤 때 모델을 미리 불러오느라 준비가 늦다 → 시간 제한 없이 기다리며 1분마다 안내
// 6) 외부 접속 터널(Cloudflare Quick Tunnel) → 다른 와이파이·LTE에서도 들어올 https 주소 안내 (tunnel.mjs)
//    실패해도 같은 와이파이 접속은 그대로 동작. 끄려면 .env 에 SERVER_TUNNEL=off
//
// 운영 데이터(DB·영수증 사진·로그인 키)는 server-data/ 에 따로 쌓인다 → 개발(start 파일, npm run dev)과
// 섞이지 않고, 둘을 동시에 켜도 된다. 개발 중에 만든 계정·조직은 여기 없음 (처음엔 회원가입부터)
import { spawnSync } from 'node:child_process'
import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import {
  BACKEND,
  FRONTEND,
  ROOT,
  SERVER_DATA_DIR,
  SERVER_PORT,
  SERVER_PORTS,
  VENV_PYTHON,
  checkOcrStatus,
  ensurePortsFree,
  isOcrSetupNeeded,
  isServerRunning,
  isSetupUpToDate,
  lanAddresses,
  ocrEngineSetting,
  openBrowser,
  runPythonForeground,
  startupSummary,
} from './lib.mjs'
import { ensureCloudflared, startQuickTunnel, tunnelEnabled } from './tunnel.mjs'

const LOCAL_URL = `http://127.0.0.1:${SERVER_PORT}`
const NOTICE_EVERY_MS = 60_000
// 지금 쓰는 외부 주소를 적어두는 파일 → 서버 파일을 또 더블클릭하면 다시 안내할 수 있게
const PUBLIC_URL_FILE = path.join(SERVER_DATA_DIR, 'public-url.txt')

// 서버 모드에서만 쓰는 백엔드 설정 (.env 보다 우선) — 데이터 위치를 개발용과 분리 + 화면도 같이 내보내기
const SERVER_ENV = {
  DATA_DIR: SERVER_DATA_DIR,
  STORAGE_DIR: path.join(SERVER_DATA_DIR, 'storage'),
  SERVE_FRONTEND: 'true',
  PYTHONUTF8: '1',
  PYTHONUNBUFFERED: '1',
}

function failWithHint(code) {
  console.error('\n[실행 실패] 위 메시지(특히 [오류]로 시작하는 줄과 Traceback)를 복사해서 보내주세요.\n')
  process.exit(code || 1)
}

/** 단계 하나 실행. 실패하면 안내 후 종료 */
function step(title, command, args, options) {
  console.log(`\n${title}`)
  const result = spawnSync(command, args, { stdio: 'inherit', ...options })
  if (result.error || result.status !== 0) {
    if (result.error) console.error(result.error.message)
    failWithHint(result.status)
  }
}

function python(title, args) {
  step(title, VENV_PYTHON, args, { cwd: BACKEND, env: { ...process.env, ...SERVER_ENV } })
}

/** 접속 주소 + 인식(OCR) 상태. OCR 줄은 어떤 경우에도 한 줄 찍는다 (서버에 못 물어보면 확인 방법 안내) */
async function printServerInfo({ elsewhere = false } = {}) {
  const ocr = await checkOcrStatus(LOCAL_URL)
  const lan = lanAddresses()
  console.log(
    elsewhere
      ? '\n>>> 공용 서버가 이미 다른 창에서 실행 중이에요 — 끄려면 그 창을 닫으세요'
      : '\n>>> 공용 서버 실행 중 — 끄려면 이 창을 닫으세요 (또는 Ctrl+C)',
  )
  console.log(`    이 노트북:                  ${LOCAL_URL}`)
  if (lan.length === 0) {
    console.log('    같은 와이파이의 PC·폰:      (와이파이·랜에 연결돼 있지 않아요)')
  }
  for (const { name, address } of lan) {
    console.log(`    같은 와이파이의 PC·폰:      http://${address}:${SERVER_PORT}   (${name})`)
  }
  console.log(`    인식(OCR):                  ${ocr.text}`)
  console.log('    - 같은 와이파이에서 안 열리면: Windows 방화벽 "허용", 학교 와이파이면 핫스팟으로')
  console.log(`    - 운영 데이터: ${SERVER_DATA_DIR}  (켤 때마다 DB 자동 백업 → server-data/backups)`)
  if (ocr.ocr === 'unavailable') {
    console.log('\n[주의] 실제 OCR이 꺼진 채로 켜졌어요 → 서버를 끄고 npm run setup:ocr 를 다시 실행해 보세요.')
    console.log('       그래도 안 되면 이 창을 맨 위부터 캡처해서 보내주세요.')
  }
}

function printPublicAddress(url) {
  console.log(`\n>>> 다른 와이파이·LTE에서도 접속:  ${url}`)
  console.log('    - 서버를 켤 때마다 주소가 바뀌어요 → 켤 때마다 이 주소를 팀에 다시 공유하세요')
  console.log('    - 주소를 아는 사람은 누구나 로그인 화면까지 들어올 수 있어요 (데이터는 로그인 + 초대 코드로 보호)')
  console.log('    - 접속 기록(누가 어떤 요청을 했는지)이 아래에 계속 찍힙니다\n')
}

/** 외부 접속 터널을 띄우고 주소를 안내한다. 실패해도 서버는 계속 (같은 와이파이 접속은 그대로) */
async function startTunnel() {
  console.log('\n    다른 와이파이·LTE에서 들어올 주소를 만드는 중... (최대 1분)')
  let binary
  try {
    binary = await ensureCloudflared()
  } catch (error) {
    console.log(`\n[주의] 외부 접속 도구를 준비하지 못했어요: ${error.message}`)
    console.log('       같은 와이파이 접속은 그대로 됩니다. 인터넷 연결을 확인하고 서버를 다시 켜 보세요.\n')
    return null
  }

  const tunnel = startQuickTunnel(binary, LOCAL_URL)
  const { url, connected } = await tunnel.ready
  if (!url) {
    tunnel.child.kill()
    console.log('\n[주의] 외부 접속 주소를 만들지 못했어요. 같은 와이파이 접속은 그대로 됩니다.')
    console.log('       → 인터넷 연결 확인 / 학교·회사 네트워크가 막았을 수 있음 → 핫스팟으로 다시 시도')
    console.log(`       cloudflared 로그 마지막 줄:\n${tunnel.recentLog().replace(/^/gm, '         ')}\n`)
    return null
  }

  writeFileSync(PUBLIC_URL_FILE, url)
  printPublicAddress(url)
  if (!connected) {
    console.log('[주의] 주소는 받았지만 연결 확인이 늦어지고 있어요. 안 열리면 이 네트워크가 막은 것 → 핫스팟으로 다시 시도\n')
  }
  tunnel.child.on('exit', () => {
    rmSync(PUBLIC_URL_FILE, { force: true })
    if (!shuttingDown) {
      console.log('\n[주의] 외부 접속(터널)이 끊겼어요. 같은 와이파이 접속은 계속 됩니다. 다시 열려면 서버 창을 닫고 다시 켜세요.\n')
    }
  })
  return tunnel.child
}

console.log('\n=== 영수증 정산 공용 서버 ===')
console.log(startupSummary())

if (await isServerRunning()) {
  await printServerInfo({ elsewhere: true })
  try {
    console.log(`    다른 와이파이·LTE에서도:   ${readFileSync(PUBLIC_URL_FILE, 'utf8').trim()}`)
  } catch {
    // 외부 주소 없음 (터널 꺼짐·실패)
  }
  console.log('')
  openBrowser(LOCAL_URL)
  process.exit(0)
}

await ensurePortsFree(SERVER_PORTS)

if (!isSetupUpToDate()) {
  step(
    '처음 실행이거나 패키지가 바뀌어서 준비(setup)부터 합니다. 몇 분 걸릴 수 있어요.',
    process.execPath,
    [path.join(ROOT, 'scripts', 'setup.mjs')],
    { cwd: ROOT, env: { ...process.env, SETUP_CALLED_BY_LAUNCHER: '1' } },
  )
}

if (isOcrSetupNeeded()) {
  step(
    '실제 OCR(OCR_ENGINE=paddle)을 쓰도록 돼 있어서 OCR 설치부터 합니다. 몇 분 걸려요.',
    process.execPath,
    [path.join(ROOT, 'scripts', 'setup-ocr.mjs')],
    { cwd: ROOT },
  )
}

const vite = path.join(FRONTEND, 'node_modules', 'vite', 'bin', 'vite.js')
step('[1/3] 화면 빌드 (frontend/dist)', process.execPath, [vite, 'build', '--logLevel', 'warn'], { cwd: FRONTEND })

mkdirSync(SERVER_DATA_DIR, { recursive: true })
rmSync(PUBLIC_URL_FILE, { force: true }) // 지난번 외부 주소는 이제 안 통함
python('[2/3] 운영 DB 백업 + 구조 업데이트 (server-data)', ['-m', 'app.ops.backup'])
python('      DB 구조 업데이트', ['-m', 'alembic', 'upgrade', 'head'])

const loadsOcrModel = ocrEngineSetting() === 'paddle'
console.log(`\n[3/3] 서버 시작 (포트 ${SERVER_PORT})`)
if (loadsOcrModel) {
  console.log('      실제 OCR 모델을 미리 불러와요 → 준비까지 10~30초 더 걸려요 (설치 직후 처음엔 더 걸릴 수 있음)')
}
// Ctrl+C로 끈 경우엔 정상 종료 (실행 파일이 에러 화면에서 멈추지 않게)
let stoppedByUser = false
let shuttingDown = false
let tunnelChild = null
process.on('SIGINT', () => {
  stoppedByUser = true
  shuttingDown = true
})
process.on('exit', () => {
  shuttingDown = true
  tunnelChild?.kill() // 서버가 꺼지면 터널도 같이 끈다 (Windows는 부모가 끝나도 자식이 남을 수 있음)
  rmSync(PUBLIC_URL_FILE, { force: true })
})
runPythonForeground(
  // 0.0.0.0 = 이 PC의 모든 네트워크 주소에서 받음 → 같은 와이파이의 다른 기기가 접속 가능
  // 워커 1개: SQLite·OCR 한 장씩 처리 구조라 프로세스를 여러 개 띄우지 않는다
  ['-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', String(SERVER_PORT)],
  SERVER_ENV,
  (code) => {
    shuttingDown = true
    if (stoppedByUser || code === 0) process.exit(0)
    failWithHint(code)
  },
)

// 준비될 때까지 기다린다. 시간 제한은 두지 않음 — 서버가 에러로 꺼지면 위 콜백이 안내 후 종료시킨다
const startedAt = Date.now()
let nextNoticeAt = NOTICE_EVERY_MS
while (!(await isServerRunning())) {
  await new Promise((resolve) => setTimeout(resolve, 700))
  const waited = Date.now() - startedAt
  if (waited >= nextNoticeAt) {
    nextNoticeAt += NOTICE_EVERY_MS
    const why = loadsOcrModel ? ' — 실제 OCR 모델을 불러오는 중일 수 있어요' : ''
    console.log(`\n[안내] 서버가 아직 준비 중이에요 (${Math.round(waited / 60_000)}분째)${why}.`)
    console.log('       위에 에러(Traceback)가 보이거나 5분이 넘도록 이러면 이 창을 캡처해서 보내주세요.\n')
  }
}

await printServerInfo()
openBrowser(LOCAL_URL)
if (tunnelEnabled()) {
  tunnelChild = await startTunnel()
} else {
  console.log('    - 외부 접속(터널)은 꺼져 있어요 (.env 의 SERVER_TUNNEL=off)')
  console.log('    - 접속 기록(누가 어떤 요청을 했는지)이 아래에 계속 찍힙니다\n')
}
