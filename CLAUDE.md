# 이 저장소를 고칠 때

Claude Code 플러그인(`seongho`)이자 마켓플레이스(`seongho-skills`)다. 에이전트는 `agents/`에 두면 자동으로 인식된다. 스킬은 그룹 폴더(`skills/pipeline/`) 안에 두며, **중첩된 스킬은 자동 인식되지 않으므로 `.claude-plugin/plugin.json`의 `skills` 배열에 경로를 직접 적는다.**

## 불변 규칙

- **새 스킬은 `.claude-plugin/plugin.json`의 `skills` 배열에 추가한다.** 빠지면 오류 없이 조용히 플러그인에서 빠진다. 스킬 폴더를 옮기거나 이름을 바꿔도 배열과 `agents/*.md`의 `../skills/pipeline/...` 링크를 함께 고친다. 새 그룹 폴더(`skills/<그룹>/`)를 만들 때도 같다.
- **스킬 간 호출은 Skill 도구로 `seongho:<이름>`을 쓴다.** 본문에 `/spec`처럼 접두사 없는 슬래시 표기를 operative 지시로 쓰지 않는다. 접두사 없는 이름은 다른 스킬과 충돌한다(`verify`가 실제로 그랬다). 사용자에게 안내하는 문구는 `/seongho:verify`처럼 접두사를 붙인다.
- `disable-model-invocation: true`인 스킬(`dev-pipeline`)은 다른 스킬이 호출할 수 없다. 파이프라인 안에서 호출되는 스킬에는 이 옵션을 붙이지 않는다.
- **스킬과 에이전트는 프로젝트 지식을 갖지 않는다.** 스택·명령·규칙은 대상 프로젝트의 `CLAUDE.md`·`AGENTS.md`·`README`에서 읽는다.
- 스펙의 완료의 정의는 `DoD-N`, 엣지 케이스는 `EC-N` ID를 쓰고, `test-design`의 `@spec` 태그가 이 ID로 연결된다. ID 규칙을 바꾸면 `check-spec.py`, `check-skeleton.py`, `test-design`, 두 테스트 에이전트를 함께 고친다.
- 파이프라인 단계를 추가·삭제·재배열하면 아래 파일의 "N단계" 참조를 모두 고친다: `skills/pipeline/dev-pipeline/SKILL.md`, `skills/pipeline/dev-pipeline/references/*.md`, `README.md`. 고친 뒤 `grep -rnE "[0-9]단계|[0-9]↔[0-9]" skills README.md`로 남은 참조를 확인한다.
- 스킬을 추가하면 `README.md`의 표와 구성 목록에 넣는다.

## 릴리스

- 플러그인 변경이 설치한 사용자에게 보이려면 `.claude-plugin/plugin.json`의 `version`을 올려야 한다.
- 커밋 전에 `scripts/validate.sh`를 실행한다. 마켓플레이스, 스킬, 에이전트, 플러그인 매니페스트를 검증하고 `plugin.json`의 `skills` 배열이 실제 스킬 폴더와 일치하는지 확인한다. 스킬이 그룹 폴더 안에 있으면 `claude plugin validate skills`가 중첩된 `SKILL.md`를 검사하지 못하므로(깨진 frontmatter도 통과한다) 이 스크립트를 쓴다. `plugin.json`만 `--strict` 없이 검사하는데, 루트의 이 `CLAUDE.md`가 "플러그인 컨텍스트로 로드되지 않는다"는 경고를 내기 때문이다(저장소 유지보수용이라 의도한 것).
- 설치 시험은 사용자 설정을 건드리지 않게 임시 설정 디렉터리에서 한다: `CLAUDE_CONFIG_DIR=$(mktemp -d) claude plugin marketplace add <이 저장소 경로>` 후 `claude plugin install seongho@seongho-skills`. 세션에서 이름을 확인할 때는 `claude --plugin-dir . -p "…"`를 쓴다.

## 외부 플러그인

- `diagram-design`은 복사하지 않고 `marketplace.json`에서 업스트림을 참조한다. 소스는 `github` 형식(SSH로 clone)이 아니라 HTTPS `url` 형식을 쓴다. SSH 키가 없는 사용자도 설치할 수 있어야 하기 때문이다.
