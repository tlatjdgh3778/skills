#!/usr/bin/env bash
# 사용법:
#   ./install.sh --global [--copy]        ~/.claude에 설치 (모든 프로젝트에서 사용)
#   ./install.sh <프로젝트 경로> [--copy]  해당 프로젝트의 .claude에 설치
# 기본은 심볼릭 링크(이 저장소를 고치면 반영). --copy는 복사.
# 이미 있는 파일은 덮어쓰지 않는다.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
FIRST="${1:?--global 또는 대상 프로젝트 경로를 지정하세요}"
MODE="${2:-link}"
if [ "$FIRST" = "--global" ]; then TARGET="$HOME"; else TARGET="$FIRST"; fi
[ -d "$TARGET" ] || { echo "대상 디렉터리가 없습니다: $TARGET" >&2; exit 1; }

DEST="$TARGET/.claude"
mkdir -p "$DEST/skills" "$DEST/agents"

place() { # place <원본> <대상>
  local from="$1" to="$2"
  if [ -e "$to" ] || [ -L "$to" ]; then
    echo "건너뜀 (이미 있음): $to"
    return
  fi
  if [ "$MODE" = "--copy" ]; then cp -R "$from" "$to"; else ln -s "$from" "$to"; fi
  echo "설치: $to"
}

for d in "$SRC"/skills/*/; do place "${d%/}" "$DEST/skills/$(basename "$d")"; done
for f in "$SRC"/agents/*.md; do place "$f" "$DEST/agents/$(basename "$f")"; done
echo "설치 완료. Claude Code 세션을 다시 시작하세요."
