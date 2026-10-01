# skills

기능 개발 수명주기를 오케스트레이션하는 Claude Code 스킬·에이전트 모음. 요청 접수 → 인터뷰 → 스펙 → 계획 → 테스트 설계(골격 동결) → 멀티 에이전트 구현 → 적대적 검증 → 사용자 검토 → 커밋 → (문제 시) 부검.

스킬과 에이전트는 **프로젝트 지식을 갖지 않는다.** 스택·명령·규칙·커밋 관례는 각 프로젝트의 `CLAUDE.md`(또는 `AGENTS.md`, `README`)와 코드베이스에서 읽는다.

## 구성

```
skills/pipeline/   dev-pipeline(오케스트레이터) interview spec plan test-design implement verify
agents/           backend-dev frontend-dev test-dev e2e-dev
scripts/          validate.sh (릴리스 전 검증)
```

| 스킬 | 역할 |
|---|---|
| `dev-pipeline` | 10단계 오케스트레이터. 직접 코드를 쓰지 않고 위임·취합·사용자 확인만 한다. 사용자가 `/seongho:dev-pipeline`으로 직접 호출한다 |
| `interview` | 결정 가능한 수준이 될 때까지 한 번에 한 주제씩 인터뷰한다. 구현하지 않는다 |
| `spec` | 확정된 결정을 다섯 장기 구조(목표·비목표·완료의 정의·인터페이스 계약·엣지 케이스)의 스펙으로 굳힌다. 완료의 정의와 엣지 케이스 항목에 `DoD-N`·`EC-N` ID를 붙인다. 저장 전에 형식 검사 스크립트를 돌린다 |
| `plan` | 스펙을 사이드별 자기완결 지시서로 분화해 계획 파일로 저장한다 |
| `test-design` | 구현 전에 스펙 항목을 테스트 골격(describe/it 서술 + given/when/then 주석)으로 먼저 고정한다. 기계 검사, 새 reviewer의 적대적 검토, mock 경계의 사람 확정을 거쳐 동결한다. 동결된 골자는 스펙이 바뀔 때만 바뀐다 |
| `implement` | 지시서를 에이전트에 위임·취합한다 (의존 순서, 병렬, 충돌 확인) |
| `verify` | 읽기 전용 적대적 검증. 구현을 신뢰하지 않고 깨뜨릴 방법을 먼저 찾는다 |

| 에이전트 | 역할 |
|---|---|
| `backend-dev` | 지시서에 따라 서버 측 코드를 구현한다 |
| `frontend-dev` | 지시서에 따라 화면 측 코드를 구현한다. 서버 계약은 소비만 한다 |
| `test-dev` | 단위·통합 테스트 코드를 **작성만** 한다(골격 모드·살 모드). 실행하지 않는다 |
| `e2e-dev` | E2E 테스트 코드를 **작성만** 한다(골격 모드·살 모드). 실행하지 않는다 |

검증(`verify`), 테스트 골격 검토, 부검은 전용 에이전트 없이 새 `general-purpose` 에이전트가 수행한다.

## 설치

### 플러그인 (권장)
```
/plugin marketplace add tlatjdgh3778/skills
/plugin install seongho@seongho-skills
```
스킬은 `seongho:` 접두사로 호출한다(예: `/seongho:dev-pipeline`). 다른 스킬과 이름이 겹치는 것을 막기 위한 것이며, 스킬끼리의 호출도 같은 이름을 쓴다. 에이전트는 `seongho:backend-dev` 같은 이름으로 보인다. `/plugin`의 Marketplaces에서 auto-update를 켜면 갱신이 자동으로 들어온다. 갱신은 `plugin.json`의 `version`이 올라간 릴리스에서만 보인다.

같은 마켓플레이스에 [diagram-design](https://github.com/cathrynlavery/diagram-design)(외부 플러그인, MIT)도 올라 있다. 이 저장소에 복사한 것이 아니라 업스트림을 직접 참조한다.
```
/plugin install diagram-design@seongho-skills
```

### 이전 방식(`install.sh`)을 썼다면
`install.sh`는 제거했다. 예전에 이 스크립트로 `~/.claude/skills`, `~/.claude/agents`(또는 프로젝트의 `.claude/`)에 링크나 복사본을 만들었다면 지운 뒤 플러그인을 설치한다. 같이 두면 스킬이 두 번 생기고, 접두사 없는 이름으로 설치된 쪽은 `seongho:` 호출과 맞지 않는다.

## 프로젝트가 준비할 것

별도 설정 파일은 없다. 프로젝트의 `CLAUDE.md`(또는 `AGENTS.md`, `README`)에 아래가 있으면 스킬과 에이전트가 읽어 쓴다. 없으면 코드베이스(설정 파일, 기존 코드)에서 확인한다.

- 빌드·타입 검사·린트·테스트·개발 서버 **명령**
- 코드 **규칙·관례**와 변경하면 안 되는 곳(생성 파일, 제공된 공통 기반)
- **커밋 메시지 관례**와 배포 절차
- (선택) 영역별로 쓸 에이전트에 대한 지침. 예: "서버 작업은 `backend-dev`"

## 사용

```
/seongho:dev-pipeline <구현하려는 기능 한 줄>
```
특정 단계부터 시작하려면 요청에 적는다 (예: "스펙은 있으니 4단계 계획부터"). 각 스킬은 단독 호출도 가능하다 (`/seongho:interview`, `/seongho:spec <기능>`, `/seongho:plan <스펙 경로>`, `/seongho:test-design <계획 파일 경로>`, `/seongho:implement <계획 파일 경로>`, `/seongho:verify <스펙 경로> [계획 파일 경로]`).

## 설계 원칙

- 오케스트레이터는 코드를 쓰지 않는다. 구현·검증은 서브 에이전트가 한다.
- **코드를 만든 에이전트는 자기 코드를 검증하지 못한다.** 테스트를 만든 에이전트는 그 테스트를 실행하지 않는다. 검증과 실행은 새 `general-purpose` 에이전트가 `verify` 스킬로 읽기 전용으로 한다.
- 결정은 사람이 한다. 스펙은 결정을 굳힐 뿐 만들지 않는다. 설계 결정은 스펙(계약)과 계획(지시서)에서 사용자 승인을 받는다.
- **테스트는 구현보다 먼저, 골자는 스펙이 바뀔 때만 바뀐다.** 스펙 항목을 골격으로 먼저 동결하고(골자 digest 기록), 검증이 digest로 골대 옮기기를 잡는다. mock 경계는 사람이 정한다.
- 결함은 원 구현 에이전트에게 재위임한다. 같은 결함이 3회 반복되면 루프를 멈추고 사용자와 상의한다.
- 스킬 본문은 얇게, 상세는 `assets/`·`references/`·`scripts/`에 두어 필요할 때만 읽는다.
- 부검이 스킬·에이전트·프로젝트 지침의 결함을 지목하면 사용자 승인 후 직접 개선한다.

## 알려진 가정

- 역할 분리(backend / frontend / e2e)는 웹 앱을 가정한다. 다른 형태의 프로젝트는 에이전트를 추가하거나 `CLAUDE.md`에 라우팅 지침을 적는다.
- 읽기 전용이 요구되는 에이전트(`verify`, 부검)는 `general-purpose`를 쓰므로 도구로 막지 못한다. 지시와 `git status` 확인으로 보장한다.
