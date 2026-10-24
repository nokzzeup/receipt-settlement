// 고정 주소(외부 접속) — Tailscale Funnel
//
// 공용 서버(serve.mjs)가 켜질 때 `tailscale funnel <포트>`를 같이 띄우면
// https://<기기 이름>.<tailnet 이름>.ts.net 주소로 인터넷 어디서나 이 PC의 서버에 들어올 수 있다.
// - Cloudflare 임시 주소(tunnel.mjs)와 달리 서버를 다시 켜도 주소가 그대로 → 폰 '홈 화면에 추가'·로그인이 유지됨
// - 무료(모든 요금제). 서버 PC만 Tailscale 설치·로그인, 접속하는 사람은 아무것도 설치하지 않음
// - 포그라운드로 실행: 이 프로세스가 끝나면(서버를 끄면) tailscaled가 Funnel 설정을 지운다
//   → 서버가 꺼져 있는 동안엔 인터넷에 열려 있지 않음 (tailscale 1.104.2 소스: DeleteForegroundSession)
// - 처음 한 번은 tailnet에서 Funnel 사용을 허용해야 한다 → CLI가 출력하는 login.tailscale.com 링크로 안내
// - 접속자 IP: Tailscale이 X-Forwarded-For에 실제 IP를 넣어 127.0.0.1에서 넘겨줌 → uvicorn이 반영 (로그인 제한용)
// CLI 사용법은 tailscale 1.104.2(2026-10) 기준으로 확인: `tailscale status --json`, `tailscale funnel <포트>`
import { spawn, spawnSync } from 'node:child_process'
import path from 'node:path'
import { createInterface } from 'node:readline'
import { isWindows, readEnvValue } from './lib.mjs'

const STATUS_TIMEOUT_MS = 15_000
const STARTING_WAIT_MS = 20_000 // PC를 막 켰을 때 Tailscale이 연결되는 동안 기다리는 시간
const READY_TIMEOUT_MS = 60_000 // 허용 링크 없이 이 시간 안에 주소가 안 나오면 실패로 봄
// 허용 링크 (브라우저로 열 거라 따옴표·공백 등 명령줄에 위험한 글자는 받지 않음)
const ENABLE_LINK = /https:\/\/login\.tailscale\.com\/[\w\-.~/?=&%+:#]+/

/** tailscale CLI 후보: .env 의 TAILSCALE_PATH → PATH 의 tailscale → 기본 설치 위치 */
function cliCandidates() {
  const custom = readEnvValue('TAILSCALE_PATH')
  if (custom) return [custom]
  const list = ['tailscale']
  if (isWindows) {
    for (const base of [process.env.ProgramFiles, 'C:\\Program Files']) {
      if (base) list.push(path.join(base, 'Tailscale', 'tailscale.exe'))
    }
  } else if (process.platform === 'darwin') {
    list.push('/Applications/Tailscale.app/Contents/MacOS/Tailscale') // 앱에 들어 있는 CLI
  }
  return list
}

function runStatus(binary) {
  return spawnSync(binary, ['status', '--json'], {
    encoding: 'utf8',
    windowsHide: true,
    timeout: STATUS_TIMEOUT_MS,
  })
}

/** 설치된 tailscale CLI 경로. 없으면 null */
export function findTailscale() {
  for (const binary of cliCandidates()) {
    const result = runStatus(binary)
    if (result.error?.code === 'ENOENT') continue
    return binary
  }
  return null
}

/**
 * `tailscale status --json` 결과를 정리한다 (테스트하기 쉽게 실행과 분리)
 * state: running | starting | needs-login | stopped | needs-approval | not-running | error
 */
export function parseStatus({ status, stdout = '', stderr = '', error }) {
  if (error) return { state: 'error', detail: error.message }
  if (status !== 0) {
    const text = `${stderr}\n${stdout}`.trim()
    if (/doesn't appear to be running|failed to connect|is Tailscale running/i.test(text)) {
      return { state: 'not-running', detail: text }
    }
    return { state: 'error', detail: text || `종료 코드 ${status}` }
  }
  let data
  try {
    data = JSON.parse(stdout)
  } catch {
    return { state: 'error', detail: 'tailscale status 결과를 읽지 못했어요' }
  }
  switch (data.BackendState) {
    case 'Running': {
      const dnsName = String(data.Self?.DNSName ?? '').replace(/\.$/, '').toLowerCase()
      if (!dnsName) return { state: 'error', detail: '이 PC의 Tailscale 주소(DNS 이름)가 없어요 → 관리 콘솔 DNS에서 MagicDNS 켜기' }
      return { state: 'running', dnsName }
    }
    case 'Starting':
    case 'NoState':
      return { state: 'starting' }
    case 'NeedsLogin':
      return { state: 'needs-login' }
    case 'Stopped':
      return { state: 'stopped' }
    case 'NeedsMachineAuth':
      return { state: 'needs-approval' }
    default:
      return { state: 'error', detail: `알 수 없는 상태: ${data.BackendState}` }
  }
}

/** Tailscale 상태. PC를 막 켜서 연결 중이면 잠깐 기다린다 */
export async function tailscaleStatus(binary) {
  const startedAt = Date.now()
  for (;;) {
    const status = parseStatus(runStatus(binary))
    if (status.state !== 'starting' || Date.now() - startedAt > STARTING_WAIT_MS) return status
    await new Promise((resolve) => setTimeout(resolve, 2000))
  }
}

/** 상태별로 고치는 방법 (Windows 기준 문구, Mac은 메뉴 막대 아이콘) */
export function statusAdvice(status) {
  const icon = isWindows ? '작업 표시줄(시계 옆) Tailscale 아이콘' : '메뉴 막대의 Tailscale 아이콘'
  switch (status.state) {
    case 'needs-login':
      return `Tailscale에 로그인이 안 돼 있어요 → ${icon} → Log in`
    case 'stopped':
      return `Tailscale 연결이 꺼져 있어요 → ${icon} → Connect`
    case 'needs-approval':
      return '이 PC가 tailnet 관리자 승인을 기다리고 있어요 → https://login.tailscale.com/admin/machines 에서 승인'
    case 'not-running':
      return 'Tailscale이 실행되고 있지 않아요 → 시작 메뉴에서 Tailscale을 실행하고 연결'
    case 'starting':
      return 'Tailscale이 아직 연결 중이에요 → 잠시 뒤 서버를 다시 켜 보세요'
    default:
      return `Tailscale 상태를 확인하지 못했어요: ${status.detail ?? status.state}`
  }
}

/**
 * Funnel 시작 (포그라운드). ready 는 { ok } 로 끝난다.
 * - 주소 줄(https://<dnsName>/)이 출력되면 성공
 * - 처음이라 tailnet에서 Funnel을 허용해야 하면 CLI가 login.tailscale.com 링크를 찍고 기다린다
 *   → onEnableLink(link) 호출, 허용될 때까지 시간 제한 없이 기다림 (그동안 같은 와이파이 접속은 됨)
 * - 그 전에 꺼지면 실패 (로그아웃, 다른 Funnel·serve 설정과 충돌 등 → recentLog 에 이유)
 */
export function startFunnel(binary, port, dnsName, { onEnableLink } = {}) {
  const url = `https://${dnsName}`
  const child = spawn(binary, ['funnel', String(port)], {
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  })
  const recent = []
  let enableLink = null

  const ready = new Promise((resolve) => {
    let settled = false
    const finish = (ok) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      resolve({ ok })
    }
    const timer = setTimeout(() => {
      if (!enableLink) finish(false) // 허용 링크를 띄운 경우엔 사람이 누를 때까지 기다림
    }, READY_TIMEOUT_MS)
    const onLine = (line) => {
      if (line.trim()) recent.push(line)
      if (recent.length > 15) recent.shift()
      const link = line.match(ENABLE_LINK)?.[0]
      if (link && !enableLink) {
        enableLink = link
        onEnableLink?.(link)
      }
      if (line.trim().toLowerCase().startsWith(url)) finish(true) // "https://<기기>.<tailnet>.ts.net/" 줄
    }
    for (const stream of [child.stdout, child.stderr]) createInterface({ input: stream }).on('line', onLine)
    child.on('error', (error) => {
      recent.push(error.message)
      finish(false)
    })
    child.on('exit', () => finish(false))
  })

  return { child, url, ready, recentLog: () => recent.join('\n') }
}
