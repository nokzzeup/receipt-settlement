#!/bin/bash
# 더블클릭 실행 (Mac). 창에서 어떻게 켤지 고릅니다: 1) 개인 로컬(이 PC에서만, 개발용)  2) 팀 공용 서버(폰·다른 PC 접속)
# 묻지 않고 바로 켜기 (터미널): ./start-mac.command server  또는  ./start-mac.command dev
# 처음이면 준비(npm run setup)부터 자동으로 합니다. 끄기: 이 터미널 창을 닫거나 Ctrl+C
# Node.js·Python이 없으면 이 프로젝트의 .tools 폴더에 자동으로 받습니다 (관리자 권한 필요 없음)
cd "$(dirname "$0")" || exit 1

# shellcheck source=scripts/bootstrap/ensure-node.sh
source scripts/bootstrap/ensure-node.sh
if ! ensure_node "$(pwd)"; then
  read -r -p "Enter를 누르면 닫힙니다..."
  exit 1
fi

node scripts/start.mjs "$@"
code=$?
if [ $code -ne 0 ]; then
  echo
  read -r -p "에러가 났습니다. 위 메시지를 확인하고 Enter를 누르면 닫힙니다..."
fi
exit $code
