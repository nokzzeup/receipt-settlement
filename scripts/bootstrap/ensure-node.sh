# start-mac.command 가 source 로 불러 쓴다 (PATH를 바꿔야 해서 source).
# Node.js 22.22 이상이 있으면 그대로 쓰고, 없으면 nodejs.org 공식 휴대용 Node.js를 .tools/ 에 받아서
# (SHA-256 확인, 관리자 권한 필요 없음, 컴퓨터에 설치하지 않음) 이 창에서만 PATH 맨 앞에 둔다.

BOOT_NODE_VERSION=24.21.0

_boot_node_ok() {
  "$1" -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit(a>22||(a===22&&b>=22)?0:1)' >/dev/null 2>&1
}

_boot_sha256() {
  if command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1"; else sha256sum "$1"; fi | cut -d' ' -f1
}

ensure_node() {
  local root="$1"
  if command -v node >/dev/null 2>&1; then
    if _boot_node_ok node; then return 0; fi
    echo "설치된 Node.js가 22.22보다 오래돼서 휴대용 Node.js ${BOOT_NODE_VERSION}을 대신 씁니다."
  fi

  local platform sum
  case "$(uname -s)-$(uname -m)" in
    Darwin-arm64) platform=darwin-arm64; sum=bed7eea5325e1108f32ce5228ddd6a5f0f08a499ee42aa7442aea583702f6057 ;;
    Darwin-x86_64) platform=darwin-x64; sum=1462cb3b3046b815cf8ea436d3da450ec1a9f11dac7e5a46b0ada5305d7e8097 ;;
    Linux-x86_64) platform=linux-x64; sum=6e1db87ef58b8819e5d5402eff1536491b18edd8eb7bee5ef7897876e88dc5ff ;;
    *)
      echo "[오류] 이 컴퓨터($(uname -s) $(uname -m))용 Node.js를 자동으로 받을 수 없어요. https://nodejs.org 에서 24 LTS를 설치하세요."
      return 1
      ;;
  esac

  local name="node-v${BOOT_NODE_VERSION}-${platform}"
  local tools="$root/.tools"
  local dir="$tools/$name"
  if [ ! -x "$dir/bin/node" ]; then
    echo
    echo "Node.js가 없어서 휴대용 Node.js ${BOOT_NODE_VERSION}을 받습니다 (약 50MB, 처음 한 번만)."
    echo "이 프로젝트의 .tools 폴더에만 들어가고 컴퓨터에 설치되지는 않아요."
    mkdir -p "$tools" || return 1
    local archive="$tools/$name.tar.gz"
    local temp="$tools/tmp-node"
    if ! curl -fL --retry 2 --progress-bar -o "$archive" "https://nodejs.org/dist/v${BOOT_NODE_VERSION}/$name.tar.gz"; then
      rm -f "$archive"
      echo "[오류] Node.js를 받지 못했어요. 인터넷 연결을 확인하고 다시 실행하세요. (또는 https://nodejs.org 에서 24 LTS 설치)"
      return 1
    fi
    if [ "$(_boot_sha256 "$archive")" != "$sum" ]; then
      rm -f "$archive"
      echo "[오류] 받은 Node.js 파일이 손상됐어요 (SHA-256 불일치). 다시 실행하세요."
      return 1
    fi
    rm -rf "$temp" && mkdir -p "$temp"
    if ! tar -xzf "$archive" -C "$temp" || ! mv "$temp/$name" "$dir"; then
      rm -rf "$temp" "$archive"
      echo "[오류] Node.js 압축을 풀지 못했어요 ($tools). 다시 실행하세요."
      return 1
    fi
    rm -rf "$temp" "$archive"
  fi
  export PATH="$dir/bin:$PATH"
  echo "휴대용 Node.js ${BOOT_NODE_VERSION} 사용 (.tools/$name)"
}
