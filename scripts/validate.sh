#!/usr/bin/env bash
# 플러그인 구성을 한 번에 검증한다. 사용법: scripts/validate.sh [저장소 경로]
#
# 스킬이 skills/pipeline/ 같은 그룹 폴더 안에 있으면 `claude plugin validate skills`가
# 중첩된 SKILL.md를 검사하지 못한다(깨진 frontmatter도 통과한다). 그래서 스킬 폴더를
# 임시 디렉터리에 평탄하게 복사해서 검사한다(검증기는 심볼릭 링크를 읽지 않는다).
set -euo pipefail

ROOT="$(cd "${1:-$(dirname "$0")/..}" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
fail=0

run() { # run <설명> <명령...>
  local label="$1"; shift
  if out="$("$@" 2>&1)"; then echo "통과: $label"; else echo "실패: $label"; echo "$out" | sed 's/^/    /'; fail=1; fi
}

mkdir -p "$TMP/skills"
while IFS= read -r d; do cp -R "$d" "$TMP/skills/$(basename "$d")"; done \
  < <(find "$ROOT/skills" -name SKILL.md -exec dirname {} \; | sort)

run "마켓플레이스 (marketplace.json)" claude plugin validate "$ROOT" --strict
run "스킬 전체 (평탄화해서 검사)" claude plugin validate "$TMP/skills" --strict
run "에이전트" claude plugin validate "$ROOT/agents" --strict
# 루트 CLAUDE.md가 "플러그인 컨텍스트로 로드되지 않는다"는 경고를 내는 것은 의도한 것이므로 --strict를 쓰지 않는다.
run "플러그인 매니페스트 (plugin.json)" claude plugin validate "$ROOT/.claude-plugin/plugin.json"

# plugin.json의 skills 배열과 실제 SKILL.md가 일치하는지: 빠지면 오류 없이 조용히 플러그인에서 빠진다.
listed="$(python3 -c 'import json,sys; [print(p) for p in sorted(json.load(open(sys.argv[1]))["skills"])]' "$ROOT/.claude-plugin/plugin.json")"
actual="$(cd "$ROOT" && find skills -name SKILL.md -exec dirname {} \; | sed 's#^#./#' | sort)"
if [ "$listed" = "$actual" ]; then echo "통과: plugin.json skills 배열과 실제 스킬 폴더 일치"
else echo "실패: plugin.json skills 배열과 실제 스킬 폴더가 다르다"; diff <(echo "$listed") <(echo "$actual") | sed 's/^/    /'; fail=1; fi

exit $fail
