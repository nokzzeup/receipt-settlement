// 컴퓨터에 쓸 수 있는 Python(3.13·3.12)이 없을 때: 휴대용 Python 3.13을 이 프로젝트의 .tools/ 에 받는다.
// - uv(Python 설치 도구, 무료·오픈소스, astral-sh/uv)를 GitHub 공식 릴리스에서 받아 SHA-256 확인
// - uv가 python-build-standalone(공식 CPython 빌드)을 .tools/python 에 설치 → 관리자 권한 필요 없음,
//   PATH·레지스트리·사용자 폴더를 건드리지 않음 (--no-bin --no-registry, 캐시도 .tools 안)
// - 백엔드 가상환경(backend/.venv)은 이 Python으로 만든다. 폴더를 옮기면 setup이 가상환경을 다시 만듦
import { spawnSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { existsSync, mkdirSync, readdirSync, renameSync, rmSync, statSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { ROOT, isWindows } from '../lib.mjs'

export const PORTABLE_PYTHON_VERSION = '3.13.15'
const UV_VERSION = '0.12.21'
// https://github.com/astral-sh/uv/releases/download/0.12.21/<파일>.sha256 값
const UV_ASSETS = {
  'win32-x64': ['uv-x86_64-pc-windows-msvc.zip', '5d223efa0bf00208c3853246af09420419dfbd352536aa6bb8163d6170e23890'],
  'win32-arm64': ['uv-aarch64-pc-windows-msvc.zip', '93ed53b94e9cec000cacdfd18ca67bc4cb2b6a5f5ec041edd7f2a3dae365ce79'],
  'darwin-arm64': ['uv-aarch64-apple-darwin.tar.gz', 'b88bda573e566ef9bced66b155fe0408626fbbc053aee1c30ba686f0728c9447'],
  'darwin-x64': ['uv-x86_64-apple-darwin.tar.gz', '2b336763b396ec6afa20c5a8b083538ca7402445b868311979d740a4344c17d8'],
  'linux-x64': ['uv-x86_64-unknown-linux-gnu.tar.gz', '23f02075b652bb1df64178cfae41b5caf160822e720e2663568f3f5d63bc52c0'],
}

const TOOLS = path.join(ROOT, '.tools')
const UV_DIR = path.join(TOOLS, `uv-${UV_VERSION}`)
const PYTHON_DIR = path.join(TOOLS, 'python')
const UV_ENV = {
  ...process.env,
  UV_PYTHON_INSTALL_DIR: PYTHON_DIR,
  UV_CACHE_DIR: path.join(TOOLS, 'uv-cache'),
  UV_NO_CONFIG: '1',
}

function findFile(dir, name) {
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry)
    if (statSync(full).isDirectory()) {
      const found = findFile(full, name)
      if (found) return found
    } else if (entry === name) {
      return full
    }
  }
  return null
}

async function ensureUv() {
  const exe = isWindows ? 'uv.exe' : 'uv'
  if (existsSync(UV_DIR)) {
    const found = findFile(UV_DIR, exe)
    if (found) return found
  }
  const asset = UV_ASSETS[`${process.platform}-${process.arch}`]
  if (!asset) {
    throw new Error(`이 컴퓨터(${process.platform}-${process.arch})용 Python을 자동으로 받을 수 없어요. python.org에서 3.13을 설치하세요.`)
  }
  const [file, sha256] = asset
  const url = `https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/${file}`
  const response = await fetch(url, { signal: AbortSignal.timeout(300_000) })
  if (!response.ok) throw new Error(`Python 설치 도구(uv)를 받지 못했어요 (HTTP ${response.status}). 인터넷 연결을 확인하세요.`)
  const data = Buffer.from(await response.arrayBuffer())
  if (createHash('sha256').update(data).digest('hex') !== sha256) {
    throw new Error('받은 Python 설치 도구(uv) 파일이 손상됐어요 (SHA-256 불일치). 다시 실행하세요.')
  }
  mkdirSync(TOOLS, { recursive: true })
  const archive = path.join(TOOLS, file)
  const temp = `${UV_DIR}.download`
  writeFileSync(archive, data)
  rmSync(temp, { recursive: true, force: true })
  mkdirSync(temp, { recursive: true })
  // Windows 10(1803)부터 들어 있는 tar.exe는 zip도 풀 수 있음
  const result = spawnSync('tar', [file.endsWith('.zip') ? '-xf' : '-xzf', archive, '-C', temp], { stdio: 'inherit' })
  rmSync(archive, { force: true })
  if (result.status !== 0) {
    rmSync(temp, { recursive: true, force: true })
    throw new Error('Python 설치 도구(uv) 압축을 풀지 못했어요.')
  }
  rmSync(UV_DIR, { recursive: true, force: true })
  renameSync(temp, UV_DIR) // 다 푼 다음 이름을 바꿔서 반쯤 풀린 폴더가 남지 않게
  const found = findFile(UV_DIR, exe)
  if (!found) throw new Error('Python 설치 도구(uv) 실행 파일을 찾지 못했어요.')
  return found
}

function uv(uvPath, args) {
  return spawnSync(uvPath, args, { env: UV_ENV, encoding: 'utf8' })
}

/** 휴대용 Python 실행 파일 경로 (없으면 받아서 설치). 실패하면 이유를 담은 Error */
export async function ensurePortablePython() {
  const uvPath = await ensureUv()
  let found = uv(uvPath, ['python', 'find', PORTABLE_PYTHON_VERSION, '--managed-python'])
  if (found.status !== 0) {
    console.log(`휴대용 Python ${PORTABLE_PYTHON_VERSION}을 받습니다 (약 30MB, 처음 한 번만). .tools 폴더에만 들어가요.`)
    const install = spawnSync(
      uvPath,
      ['python', 'install', PORTABLE_PYTHON_VERSION, '--no-bin', '--no-registry'],
      { env: UV_ENV, stdio: 'inherit' },
    )
    if (install.status !== 0) throw new Error('휴대용 Python을 설치하지 못했어요. 인터넷 연결을 확인하고 다시 실행하세요.')
    found = uv(uvPath, ['python', 'find', PORTABLE_PYTHON_VERSION, '--managed-python'])
  }
  const pythonPath = found.stdout?.trim()
  if (found.status !== 0 || !pythonPath || !existsSync(pythonPath)) {
    throw new Error('설치한 휴대용 Python을 찾지 못했어요. .tools/python 폴더를 지우고 다시 실행하세요.')
  }
  return pythonPath
}
