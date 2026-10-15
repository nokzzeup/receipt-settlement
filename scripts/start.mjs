// 더블클릭 실행 파일(start-windows.bat / start-mac.command)이 부르는 첫 화면: 어떻게 켤지 묻고 실행한다
//   1) 개인 로컬    → launch.mjs (= npm start)     이 PC에서만 접속, 데이터는 backend/data
//   2) 팀 공용 서버 → serve.mjs  (= npm run serve) 폰·다른 PC에서도 접속, 데이터는 server-data
// 묻지 않고 바로 켜기: start-windows.bat server  /  ./start-mac.command server  (dev 도 됨)
//   → Windows 바로 가기의 '대상' 끝에 server 를 붙여두면 더블클릭 한 번으로 서버가 켜진다
// .bat 파일은 영어만 쓸 수 있어서(cmd.exe가 OS 인코딩으로 읽음) 한글 메뉴는 여기서 출력한다
import readline from 'node:readline'
import { isWindows } from './lib.mjs'

const MODES = {
  dev: { script: './launch.mjs', title: '영수증 정산 - 개인 로컬' },
  server: { script: './serve.mjs', title: '영수증 정산 - 팀 공용 서버' },
}
// 실행 인자·메뉴 입력으로 받는 이름
const NAMES = { 1: 'dev', dev: 'dev', local: 'dev', 2: 'server', server: 'server', serve: 'server' }

/** '2', ' Server ', '２'(전각) → 'server'. 모르는 값이면 undefined */
function modeFrom(text) {
  const key = text.normalize('NFKC').trim().toLowerCase()
  return Object.hasOwn(NAMES, key) ? NAMES[key] : undefined
}

function askMode() {
  console.log('\n=== 영수증 정산 ===')
  console.log('어떻게 켤까요?')
  console.log('  1) 개인 로컬    — 이 PC에서만 접속 (개발·테스트용, 데이터: backend/data)')
  console.log('  2) 팀 공용 서버 — 폰·다른 PC에서도 접속 (이 PC를 켜두기, 데이터: server-data)')
  console.log('번호를 누르고 Enter (그냥 Enter = 1)')

  const terminal = Boolean(process.stdin.isTTY && process.stdout.isTTY)
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout, terminal })
  return new Promise((resolve) => {
    let done = false
    rl.on('line', (line) => {
      const mode = line.trim() === '' ? 'dev' : modeFrom(line)
      if (!mode) {
        console.log('1 또는 2를 입력하세요.')
        rl.prompt()
        return
      }
      done = true
      rl.close() // 입력 모드를 원래대로 → 이후 Ctrl+C로 서버를 끌 수 있게
      resolve(mode)
    })
    // 메뉴에서 Ctrl+C: 아무것도 켜지 않고 닫기 (실행 파일이 에러 화면에서 멈추지 않게 정상 종료)
    rl.on('SIGINT', () => {
      done = true
      rl.close()
      console.log('\n취소했어요.')
      process.exit(0)
    })
    // 입력이 끝남(파이프·Ctrl+D 등) → 기본값
    rl.on('close', () => {
      if (done) return
      console.log('\n(입력이 없어서 1번 개인 로컬로 켭니다)')
      resolve('dev')
    })
    rl.setPrompt('> ')
    rl.prompt()
  })
}

/** 창 제목 — 개인 로컬과 서버를 동시에 켰을 때 작업 표시줄·탭에서 구분되게 */
function setWindowTitle(title) {
  if (isWindows) {
    process.title = title // Windows는 콘솔 창 제목이 바뀜
  } else if (process.stdout.isTTY) {
    process.stdout.write(`\x1b]0;${title}\x07`) // Mac 터미널 창 제목
  }
}

const arg = process.argv[2]
let mode = arg ? modeFrom(arg) : undefined
if (arg && !mode) console.log(`\n[주의] 모르는 실행 옵션 "${arg}" → dev(개인 로컬) 또는 server(팀 공용 서버)만 돼요.`)
mode ??= await askMode()

setWindowTitle(MODES[mode].title)
await import(MODES[mode].script)
