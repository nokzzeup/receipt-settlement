#!/bin/bash
# 더블클릭 실행 (Mac). 처음이면 준비(npm run setup)부터 자동으로 하고, 준비되면 브라우저를 엽니다.
# 끄기: 이 터미널 창을 닫거나 Ctrl+C
cd "$(dirname "$0")" || exit 1

if ! command -v node >/dev/null 2>&1; then
  echo "[오류] Node.js가 없습니다. https://nodejs.org 에서 24 LTS를 설치한 뒤 다시 실행하세요."
  read -r -p "Enter를 누르면 닫힙니다..."
  exit 1
fi

node scripts/launch.mjs
code=$?
if [ $code -ne 0 ]; then
  echo
  read -r -p "에러가 났습니다. 위 메시지를 확인하고 Enter를 누르면 닫힙니다..."
fi
exit $code
