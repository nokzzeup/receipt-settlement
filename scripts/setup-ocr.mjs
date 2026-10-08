// npm run setup:ocr — 실제 OCR(PaddleOCR) 설치. 팀 공용 서버로 쓰는 PC와 OCR 담당만 하면 된다
//
// 1) 기본 준비(setup)가 됐는지 → 안 됐으면 먼저
// 2) 이 컴퓨터용 설치 파일이 있는지 (Windows x64, Apple Silicon Mac, Linux x64)
// 3) 서버가 꺼져 있는지 (켜진 채로 패키지를 바꾸면 Windows에서 설치가 깨짐)
// 4) 패키지 설치 (backend/requirements-ocr.txt, 내려받는 양 약 300MB — 몇 분 걸림)
// 5) 자가 진단: 모델 파일(약 25MB) 받기 + 시험 이미지 인식
// 6) .env 의 OCR_ENGINE 을 paddle 로 바꿈 → 다음 실행부터 업로드하면 실제로 인식
//
// OCR_ENGINE=paddle 인데 설치가 안 돼 있으면 더블클릭 실행(start·server 파일)이 이 스크립트를 자동으로 부른다
import { spawnSync } from 'node:child_process'
import { readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import {
  BACKEND,
  DEV_PORTS,
  ROOT,
  SERVER_PORTS,
  VENV_PYTHON,
  ensurePortsFree,
  fail,
  isSetupUpToDate,
  writeOcrStamp,
} from './lib.mjs'

// paddlepaddle 3.3.1 설치 파일(wheel)이 있는 조합 (2026-10-08 PyPI 확인)
const SUPPORTED = new Set(['win32-x64', 'darwin-arm64', 'linux-x64'])

const PYTHON_ENV = { ...process.env, PYTHONUTF8: '1', PYTHONUNBUFFERED: '1' }

function step(title, command, args, options = {}) {
  console.log(`\n${title}`)
  const result = spawnSync(command, args, { stdio: 'inherit', ...options })
  return !result.error && result.status === 0
}

/** .env 의 OCR_ENGINE 줄을 paddle 로 (없으면 추가) */
function switchEnvToPaddle() {
  const envFile = path.join(ROOT, '.env')
  let text = ''
  try {
    text = readFileSync(envFile, 'utf8')
  } catch {
    // .env 가 없으면 새로 만듦 (보통은 setup이 이미 만들어 둠)
  }
  const line = /^\s*OCR_ENGINE\s*=.*$/m
  const next = line.test(text) ? text.replace(line, 'OCR_ENGINE=paddle') : `${text.trimEnd()}\nOCR_ENGINE=paddle\n`
  if (next !== text) writeFileSync(envFile, next)
}

console.log('\n=== 실제 OCR(PaddleOCR) 설치 ===')

const platform = `${process.platform}-${process.arch}`
if (!SUPPORTED.has(platform)) {
  fail(
    `이 컴퓨터(${platform})용 PaddleOCR 설치 파일이 없어요 (Intel Mac·ARM 윈도우 등).\n` +
      '        → 이 PC는 OCR_ENGINE=mock 으로 개발하고, 실제 인식은 공용 서버 PC에서 확인하세요.',
  )
}

if (!isSetupUpToDate()) {
  const ok = step('기본 준비(setup)부터 합니다.', process.execPath, [path.join(ROOT, 'scripts', 'setup.mjs')], {
    cwd: ROOT,
    env: { ...process.env, SETUP_CALLED_BY_LAUNCHER: '1' },
  })
  if (!ok) fail('기본 준비(setup)에 실패했어요. 위 메시지를 확인하세요.')
}

await ensurePortsFree([...DEV_PORTS, ...SERVER_PORTS])

const installed = step(
  '[1/2] OCR 패키지 설치 (backend/requirements-ocr.txt) — 약 300MB를 내려받아서 몇 분 걸려요',
  VENV_PYTHON,
  ['-m', 'pip', 'install', '--disable-pip-version-check', '-r', 'requirements-ocr.txt'],
  { cwd: BACKEND, env: PYTHON_ENV },
)
if (!installed) {
  fail('OCR 패키지 설치에 실패했어요. 인터넷 연결을 확인하고 다시 실행하세요. 계속 실패하면 위 메시지를 보내주세요.')
}

const works = step('[2/2] 자가 진단 (처음이면 모델 파일 약 25MB를 내려받아요)', VENV_PYTHON, ['-m', 'app.ocr.selftest'], {
  cwd: BACKEND,
  env: PYTHON_ENV,
})
if (!works) {
  fail('설치는 됐지만 시험 인식에 실패했어요. 위 메시지(특히 Traceback)를 복사해서 보내주세요.')
}

writeOcrStamp()
switchEnvToPaddle()
console.log('\n실제 OCR 준비 완료! .env 의 OCR_ENGINE 을 paddle 로 바꿨어요 (되돌리려면 mock).')
console.log('이제 서버를 켜고(server·start 파일) 영수증을 올리면 실제로 인식합니다. 한 장에 몇 초 걸려요.\n')
