#!/bin/bash
# 더블클릭 실행 (Mac): 이 PC를 팀 공용 서버로 켭니다. 같은 와이파이의 다른 PC·폰은 창에 뜨는 주소로 접속
# 운영 데이터(DB·영수증 사진)는 server-data 폴더에 따로 쌓입니다. 끄기: 이 터미널 창을 닫거나 Ctrl+C
# Node.js·Python이 없으면 이 프로젝트의 .tools 폴더에 자동으로 받습니다 (관리자 권한 필요 없음)
cd "$(dirname "$0")" || exit 1

# shellcheck source=scripts/bootstrap/ensure-node.sh
source scripts/bootstrap/ensure-node.sh
if ! ensure_node "$(pwd)"; then
  read -r -p "Enter를 누르면 닫힙니다..."
  exit 1
fi

node scripts/serve.mjs
code=$?
if [ $code -ne 0 ]; then
  echo
  read -r -p "에러가 났습니다. 위 메시지를 확인하고 Enter를 누르면 닫힙니다..."
fi
exit $code
