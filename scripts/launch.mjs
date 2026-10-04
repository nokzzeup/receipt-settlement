// 더블클릭 실행(start-windows.bat / start-mac.command)과 `npm start`가 부르는 스크립트
// 1) 이미 실행 중이면 브라우저만 연다
// 2) 처음이거나 패키지 목록이 바뀌었으면(git pull 등) setup부터 자동으로 한다
// 3) 백엔드 + 프론트를 띄우고, 둘 다 응답하면 브라우저를 연다
import path from 'node:path'
import { APP_URL, ROOT, isAppRunning, isSetupUpToDate, openBrowser, run, runForeground } from './lib.mjs'

const SCRIPTS = path.join(ROOT, 'scripts')
const READY_TIMEOUT_MS = 120_000

console.log('\n=== 영수증 정산 개발 서버 ===')

if (await isAppRunning()) {
  console.log('이미 실행 중이라 브라우저만 엽니다.')
  openBrowser(APP_URL)
  process.exit(0)
}

if (!isSetupUpToDate()) {
  console.log('처음 실행이거나 패키지가 바뀌어서 준비(setup)부터 합니다. 몇 분 걸릴 수 있어요.')
  run(process.execPath, [path.join(SCRIPTS, 'setup.mjs')], { cwd: ROOT })
}

// Ctrl+C로 끈 경우엔 정상 종료로 처리 (실행 파일이 에러 화면에서 멈추지 않게)
let stoppedByUser = false
process.on('SIGINT', () => {
  stoppedByUser = true
})

runForeground(process.execPath, [path.join(SCRIPTS, 'dev.mjs')], { cwd: ROOT }, (code) => {
  process.exit(stoppedByUser ? 0 : code)
})

const startedAt = Date.now()
while (Date.now() - startedAt < READY_TIMEOUT_MS) {
  await new Promise((resolve) => setTimeout(resolve, 700))
  if (await isAppRunning()) {
    openBrowser(APP_URL)
    console.log(`\n>>> 준비 완료: ${APP_URL} 을 브라우저로 열었어요. 끄려면 이 창을 닫으세요 (또는 Ctrl+C).\n`)
    break
  }
}
