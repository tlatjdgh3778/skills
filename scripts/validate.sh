#!/usr/bin/env bash
# 플러그인 구성을 한 번에 검증한다. 사용법: scripts/validate.sh [저장소 경로]
set -euo pipefail

ROOT="$(cd "${1:-$(dirname "$0")/..}" && pwd)"
PLUGIN="$ROOT/dev-pipeline"
fail=0

run() { # run <설명> <명령...>
  local label="$1"; shift
  if out="$("$@" 2>&1)"; then echo "통과: $label"; else echo "실패: $label"; echo "$out" | sed 's/^/    /'; fail=1; fi
}

run "마켓플레이스 (marketplace.json)" claude plugin validate "$ROOT" --strict
run "플러그인 매니페스트 (dev-pipeline/.claude-plugin/plugin.json)" claude plugin validate "$PLUGIN/.claude-plugin/plugin.json" --strict
run "스킬 (dev-pipeline/skills)" claude plugin validate "$PLUGIN/skills" --strict
run "에이전트 (dev-pipeline/agents)" claude plugin validate "$PLUGIN/agents" --strict

exit $fail
