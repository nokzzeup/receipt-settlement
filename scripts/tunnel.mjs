// 외부 접속(다른 와이파이·LTE)용 터널 — Cloudflare Quick Tunnel
//
// 공용 서버(serve.mjs)가 켜지면 cloudflared를 같이 띄워서 https://무작위.trycloudflare.com 주소를 받는다.
// 그 주소로 들어온 요청은 Cloudflare를 거쳐 이 PC의 서버(127.0.0.1:포트)로 전달된다.
// - 무료, 계정·도메인 필요 없음, https라서 폰에서 앱처럼 설치(홈 화면 추가)도 가능
// - 대신 켤 때마다 주소가 바뀌고, Cloudflare는 "테스트·개발용, 가동 보장 없음"이라고 안내함
//   → 고정 주소가 필요해지면(실사용 테스트) Tailscale Funnel 등으로 바꾼다 (docs/DECISIONS.md)
//
// cloudflared 실행 파일은 처음 한 번 공식 GitHub 릴리스에서 내려받아 .tools/ 에 둔다 (git 제외).
// 버전을 고정하고, 내려받은 파일의 SHA-256이 아래 값과 다르면 실행하지 않는다.
import { spawn, spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { chmodSync, existsSync, mkdirSync, renameSync, rmSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { createInterface } from 'node:readline'
import { ROOT, isWindows, readEnvValue } from './lib.mjs'

export const CLOUDFLARED_VERSION = '2026.10.0'

const WINDOWS_X64 = {
  file: 'cloudflared-windows-amd64.exe',
  sha256: '86aee4017b26625cee8484c113558f48effa4cd47f7aa05fcf425604e5d2b23c',
  mb: 55,
}
const ASSETS = {
  'win32-x64': WINDOWS_X64,
  'win32-arm64': WINDOWS_X64, // ARM 윈도우는 x64 에뮬레이션으로 실행
  'darwin-arm64': {
    file: 'cloudflared-darwin-arm64.tgz',
    sha256: 'a2f79ff7b9420aa537d74af239f376da170bbabeb529aec416002adac6a72e70',
    mb: 20,
    tgz: true,
  },
  'darwin-x64': {
    file: 'cloudflared-darwin-amd64.tgz',
    sha256: '903845b81828c8cb3c5d13d816a2de71c06a3da5785469df8eb0e1b736d92f9f',
    mb: 22,
    tgz: true,
  },
  'linux-x64': {
    file: 'cloudflared-linux-amd64',
    sha256: 'd33ff2d14475178d2012c2c56beba87389ac5ded27649519f198a7d3134a99db',
    mb: 40,
  },
}

const TOOLS_DIR = path.join(ROOT, '.tools', `cloudflared-${CLOUDFLARED_VERSION}`)
const BINARY = path.join(TOOLS_DIR, isWindows ? 'cloudflared.exe' : 'cloudflared')
const URL_PATTERN = /https:\/\/[-a-z0-9]+\.trycloudflare\.com/
const READY_TIMEOUT_MS = 60_000

/** 터널 사용 여부: .env 의 SERVER_TUNNEL=off 면 끔 (기본 켬) */
export function tunnelEnabled() {
  return (readEnvValue('SERVER_TUNNEL') ?? '').trim().toLowerCase() !== 'off'
}

/** cloudflared 실행 파일 경로. 없으면 내려받는다. 실패하면 Error */
export async function ensureCloudflared() {
  const custom = readEnvValue('CLOUDFLARED_PATH') // 이미 설치한 cloudflared를 쓰고 싶을 때
  if (custom) return custom
  if (existsSync(BINARY)) return BINARY

  const asset = ASSETS[`${process.platform}-${process.arch}`]
  if (!asset) throw new Error(`이 컴퓨터(${process.platform}-${process.arch})용 cloudflared 파일이 없어요`)
  const url = `https://github.com/cloudflare/cloudflared/releases/download/${CLOUDFLARED_VERSION}/${asset.file}`
  console.log(`    외부 접속 도구(cloudflared ${CLOUDFLARED_VERSION})를 처음 한 번 내려받는 중... (약 ${asset.mb}MB)`)

  const response = await fetch(url, { signal: AbortSignal.timeout(300_000) })
  if (!response.ok) throw new Error(`내려받기 실패 (HTTP ${response.status})`)
  const data = Buffer.from(await response.arrayBuffer())
  if (createHash('sha256').update(data).digest('hex') !== asset.sha256) {
    throw new Error('내려받은 파일이 공식 파일과 달라요(손상 또는 변조) → 실행하지 않습니다. 다시 시도해 보세요')
  }

  mkdirSync(TOOLS_DIR, { recursive: true })
  if (asset.tgz) {
    const archive = path.join(TOOLS_DIR, asset.file)
    writeFileSync(archive, data)
    const result = spawnSync('tar', ['-xzf', archive, '-C', TOOLS_DIR])
    rmSync(archive, { force: true })
    if (result.status !== 0 || !existsSync(BINARY)) throw new Error('cloudflared 압축 풀기 실패')
  } else {
    const temp = `${BINARY}.download` // 다 쓴 다음 이름을 바꿔서 반쯤 받은 파일이 남지 않게
    writeFileSync(temp, data)
    renameSync(temp, BINARY)
  }
  if (!isWindows) chmodSync(BINARY, 0o755)
  return BINARY
}

/**
 * Quick Tunnel 시작. ready 는 { url, connected } (주소를 못 받으면 url = null) 로 끝난다.
 * - url: cloudflared가 출력한 https://….trycloudflare.com
 * - connected: Cloudflare와 연결까지 확인됐는지 (주소만 받고 연결이 막히는 네트워크도 있음)
 */
export function startQuickTunnel(binary, targetUrl) {
  // localhost 대신 127.0.0.1: Windows에선 localhost가 IPv6(::1)로 풀리는데 서버는 IPv4(0.0.0.0)에서만 받음
  const child = spawn(binary, ['tunnel', '--no-autoupdate', '--url', targetUrl], {
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  })
  const recent = []
  let url = null

  const ready = new Promise((resolve) => {
    let settled = false
    const finish = (connected) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      resolve({ url, connected })
    }
    const timer = setTimeout(() => finish(false), READY_TIMEOUT_MS)
    const onLine = (line) => {
      recent.push(line)
      if (recent.length > 12) recent.shift()
      url ??= line.match(URL_PATTERN)?.[0] ?? null
      if (url && /Registered tunnel connection/i.test(line)) finish(true)
    }
    for (const stream of [child.stdout, child.stderr]) createInterface({ input: stream }).on('line', onLine)
    child.on('error', (error) => {
      recent.push(error.message)
      url = null
      finish(false)
    })
    child.on('exit', () => {
      if (!settled) url = null // 주소를 받기 전에(또는 받자마자) 꺼짐 → 실패
      finish(false)
    })
  })

  return { child, ready, recentLog: () => recent.join('\n') }
}
