// 더블클릭 실행(start-windows.bat / start-mac.command)과 `npm start`가 부르는 스크립트
// 1) 이미 실행 중이면 브라우저만 연다
// 2) 포트가 막혀 있으면(다른 창에 서버가 켜져 있는 등) 이유를 알려주고 멈춘다
// 3) 처음이거나 패키지 목록이 바뀌었으면(git pull 등) setup부터 자동으로 한다
//    .env 가 실제 OCR(OCR_ENGINE=paddle)이면 OCR 설치(setup:ocr)도 필요할 때 자동으로
// 4) 백엔드 + 프론트를 띄우고, 둘 다 응답하면 브라우저를 연다
import { spawnSync } from 'node:child_process'
import path from 'node:path'
import {
  APP_URL,
  ROOT,
  ensurePortsFree,
  isAppRunning,
  isOcrSetupNeeded,
  isSetupUpToDate,
  openBrowser,
  runForeground,
} from './lib.mjs'

const SCRIPTS = path.join(ROOT, 'scripts')
const READY_TIMEOUT_MS = 120_000

function failWithHint(code) {
  console.error('\n[실행 실패] 위 메시지(특히 [오류]·[api]·[web]로 시작하는 줄)를 복사해서 보내주세요.\n')
  process.exit(code || 1)
}

console.log('\n=== 영수증 정산 개발 서버 ===')

if (await isAppRunning()) {
  console.log(`이미 실행 중이라 브라우저만 엽니다: ${APP_URL}`)
  openBrowser(APP_URL)
  process.exit(0)
}

await ensurePortsFree()

if (!isSetupUpToDate()) {
  console.log('처음 실행이거나 패키지가 바뀌어서 준비(setup)부터 합니다. 몇 분 걸릴 수 있어요.')
  const setup = spawnSync(process.execPath, [path.join(SCRIPTS, 'setup.mjs')], {
    cwd: ROOT,
    stdio: 'inherit',
    env: { ...process.env, SETUP_CALLED_BY_LAUNCHER: '1' },
  })
  if (setup.status !== 0) failWithHint(setup.status)
}

// .env 에서 실제 OCR(OCR_ENGINE=paddle)을 골랐는데 설치가 안 됐거나 버전 목록이 바뀌었으면 설치부터
if (isOcrSetupNeeded()) {
  console.log('실제 OCR(OCR_ENGINE=paddle)을 쓰도록 돼 있어서 OCR 설치부터 합니다. 몇 분 걸려요.')
  const setupOcr = spawnSync(process.execPath, [path.join(SCRIPTS, 'setup-ocr.mjs')], { cwd: ROOT, stdio: 'inherit' })
  if (setupOcr.status !== 0) failWithHint(setupOcr.status)
}

// Ctrl+C로 끈 경우엔 정상 종료로 처리 (실행 파일이 에러 화면에서 멈추지 않게)
let stoppedByUser = false
process.on('SIGINT', () => {
  stoppedByUser = true
})

runForeground(process.execPath, [path.join(SCRIPTS, 'dev.mjs')], { cwd: ROOT }, (code) => {
  if (stoppedByUser || code === 0) process.exit(0)
  failWithHint(code)
})

const startedAt = Date.now()
let ready = false
while (Date.now() - startedAt < READY_TIMEOUT_MS) {
  await new Promise((resolve) => setTimeout(resolve, 700))
  if (await isAppRunning()) {
    ready = true
    break
  }
}
if (ready) {
  openBrowser(APP_URL)
  console.log(`\n>>> 준비 완료: ${APP_URL} 을 브라우저로 열었어요. 끄려면 이 창을 닫으세요 (또는 Ctrl+C).\n`)
} else {
  console.log('\n[주의] 2분이 지나도 서버가 응답하지 않아요. 위 [api]·[web] 로그에 에러가 있으면 복사해서 보내주세요.\n')
}
