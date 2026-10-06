# 이 저장소를 고칠 때

마켓플레이스(`seongho-skills`) 저장소다. 플러그인은 하위 폴더 단위로 둔다.

```
.claude-plugin/marketplace.json     마켓플레이스 목록 (플러그인별 source)
dev-pipeline/                       플러그인 `seongho`의 루트 (source: ./dev-pipeline)
  .claude-plugin/plugin.json
  skills/<이름>/SKILL.md            자동 인식 (경로 배열 불필요)
  agents/<이름>.md                  자동 인식
scripts/validate.sh                 릴리스 전 검증
```

- 새 플러그인은 `<플러그인 폴더>/`를 만들고 `marketplace.json`의 `plugins`에 `source`와 함께 추가한다.
- `diagram-design`은 복사하지 않고 업스트림을 참조한다. 소스는 `github` 형식(SSH로 clone)이 아니라 HTTPS `url` 형식을 쓴다. SSH 키가 없는 사용자도 설치할 수 있어야 하기 때문이다.
- 이 파일은 플러그인 루트 밖에 있어서 사용자 세션에는 로드되지 않고, 이 저장소를 고치는 세션에서만 쓰인다.

## 불변 규칙

- **스킬 간 호출은 Skill 도구로 `seongho:<이름>`을 쓴다.** 본문에 `/spec`처럼 접두사 없는 슬래시 표기를 operative 지시로 쓰지 않는다. 접두사 없는 이름은 다른 스킬과 충돌한다(`verify`가 실제로 그랬다). 사용자에게 안내하는 문구는 `/seongho:verify`처럼 접두사를 붙인다.
- `disable-model-invocation: true`인 스킬(`dev-pipeline`)은 다른 스킬이 호출할 수 없다. 파이프라인 안에서 호출되는 스킬에는 이 옵션을 붙이지 않는다.
- **스킬과 에이전트는 프로젝트 지식을 갖지 않는다.** 스택·명령·규칙은 대상 프로젝트의 `CLAUDE.md`·`README`에서 읽는다.
- 스펙의 완료의 정의는 `DoD-N`, 엣지 케이스는 `EC-N` ID를 쓰고, `test-design`의 `@spec` 태그가 이 ID로 연결된다. ID 규칙을 바꾸면 `check-spec.py`, `check-skeleton.py`, `test-design`, 두 테스트 에이전트를 함께 고친다.
- 파이프라인 단계를 추가·삭제·재배열하면 아래 파일의 "N단계" 참조를 모두 고친다: `dev-pipeline/skills/dev-pipeline/SKILL.md`, `dev-pipeline/skills/dev-pipeline/references/*.md`, `README.md`. 고친 뒤 `grep -rnE "[0-9]단계|[0-9]↔[0-9]" dev-pipeline README.md`로 남은 참조를 확인한다.
- **계획 파일에 지시서(에이전트용 작업 지시)를 저장하지 않는다.** 계획에는 Task만 두고 스펙은 `연결 항목`(`DoD-N`·`EC-N`)으로 가리킨다. 작업 지시는 `implement`·`test-design`이 위임할 때 조립한다. 용어: 계획 안의 단위는 "Task", 에이전트에 넘기는 조립물은 "작업 지시"다. 계획 형식을 바꾸면 `plan`의 `check-plan.py`, `plan-template.md`, `implement`·`test-design`의 조립 규칙, 에이전트 4개를 함께 고친다.
- **파이프라인 커밋은 `git-commit-rules`의 `session-stamp.mjs`로 한다.** `Session` 트레일러 규칙과 `hooks/hooks.json`의 SessionStart 훅은 한 쌍이다. 한쪽을 바꾸면 다른 쪽과 `commit-and-revert.md`, `dev-pipeline/SKILL.md` 9단계를 함께 고친다.
- 검증 역할은 `verify`(읽기 전용 대조), `test-runner`, `e2e-runner` 셋으로 나뉜다. 한쪽의 책임을 바꾸면 `verification-loop.md`의 역할표와 취합 규칙, `dev-pipeline/SKILL.md` 7단계, `README.md`를 함께 고친다.
- 스킬을 추가하면 `README.md`의 표와 구성 목록에 넣는다.
- 에이전트의 `../skills/...` 링크는 플러그인 루트(`dev-pipeline/`) 기준 상대경로다. 폴더를 옮기면 함께 고친다.

## 릴리스

- 플러그인 변경이 설치한 사용자에게 보이려면 `dev-pipeline/.claude-plugin/plugin.json`의 `version`을 올려야 한다.
- 커밋 전에 `scripts/validate.sh`를 실행한다(마켓플레이스, 플러그인 매니페스트, 스킬, 에이전트를 `--strict`로 검증).
- 설치 시험은 사용자 설정을 건드리지 않게 임시 설정 디렉터리에서 한다: `CLAUDE_CONFIG_DIR=$(mktemp -d) claude plugin marketplace add <이 저장소 경로>` 후 `claude plugin install seongho@seongho-skills`. 세션에서 이름을 확인할 때는 `claude --plugin-dir dev-pipeline -p "…"`를 쓴다.
