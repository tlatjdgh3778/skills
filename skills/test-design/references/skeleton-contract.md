# 테스트 골격 계약

## 목적

골격은 구현 전에 스펙의 의미를 테스트 구조로 고정한다. 실행 가능한 assertion이나 제품 구조를 미리 발명하지 않는다. 골격의 조건 서술은 스펙 문구에서 가져오며, 스펙이 바뀔 때만 바뀐다.

## 스펙 → 골격 매핑

```
스펙 목표                    → 최상위 describe (사용자 결과의 언어로)
행동·상태·실패·복구 영역      → 하위 describe
항목(DoD-N·EC-N)의 결과 1개  → case 1개
전제·행동·결과               → @given · @when · @then
```

- 한 항목에 독립된 결과가 둘 이상이면 case를 나눈다(예: "401을 반환하고 세션을 만들지 않는다" → 둘).
- 한 case가 여러 항목을 함께 검증해도 된다(주로 E2E). `@spec`에 공백으로 구분해 모두 적고, case 제목에도 ID를 넣는다.
- 파일·함수·컴포넌트 이름을 행동 의미 대신 describe 이름으로 쓰지 않는다.

## 태그 주석 (언어 공통, 기계 검사 대상)

각 case 선언 **바로 앞**(데코레이터·애노테이션 앞)에 아래 네 줄을 둔다. 한 태그는 한 줄이며, 주석 문법은 언어 관례를 따른다.

```
@spec DoD-3 EC-1
@given 만료된 토큰으로 요청한다
@when 로그인 API를 호출한다
@then 401을 반환한다
```

- `@spec`의 ID는 스펙에 실제로 있는 `DoD-N`·`EC-N`이어야 한다.
- 태그 내용은 기대 결과를 약화하지 않는다. 구현이 내는 값을 베끼지 않는다.

## 미구현 표기

골격 case는 통과로 세지지 않도록 **runner의 공식 미구현·보류 표기**를 쓴다. 빈 본문의 일반 테스트는 항상 통과하므로 쓰지 않는다. 어떤 표기를 쓸지는 프로젝트의 기존 테스트 도구에서 확인한다.

| 도구 | 표기 |
|---|---|
| Vitest·Jest | `it.todo("...")` |
| Playwright | `test.fixme("...", async () => {})` (`test.skip`은 "적용 불가"를 뜻하므로 쓰지 않는다) |
| pytest | `@pytest.mark.skip(reason="skeleton")` |
| JUnit | `@Disabled("skeleton")` |
| Go | 본문에 `t.Skip("skeleton")` |

표기는 case 선언 줄 또는 바로 뒤 몇 줄 안에 있어야 한다(`check-skeleton.py`가 확인한다). 위에 없는 도구는 해당 도구의 보류 표기를 쓰고 `skeleton`임을 사유에 적는다.

## 예시

단위·통합 (Vitest):

```ts
import { describe, it } from "vitest";

describe("로그인 — 유효한 사용자가 세션을 얻는다", () => {
  describe("토큰이 만료된 경우", () => {
    /**
     * @spec DoD-3
     * @given 만료된 토큰으로 요청한다
     * @when 로그인 API를 호출한다
     * @then 401을 반환한다
     */
    it.todo("[DoD-3] 401을 반환한다");

    /**
     * @spec DoD-3
     * @given 만료된 토큰으로 요청한다
     * @when 로그인 API를 호출한다
     * @then 세션이 생성되지 않는다
     */
    it.todo("[DoD-3] 세션을 만들지 않는다");
  });
});
```

E2E (Playwright):

```ts
import { test } from "@playwright/test";

test.describe("로그인 — 유효한 사용자가 세션을 얻는다", () => {
  /**
   * @spec DoD-1 DoD-2
   * @given 로그인 페이지에서 유효한 계정을 입력했다
   * @when 로그인 버튼을 누른다
   * @then 홈으로 이동하고 세션 쿠키가 생긴다
   */
  test.fixme("[DoD-1][DoD-2] 로그인 후 홈으로 이동한다", async ({ page }) => {
    // 살은 구현 단계에서 e2e-dev가 채운다
  });
});
```

Python (pytest):

```python
# @spec DoD-3
# @given 만료된 토큰으로 요청한다
# @when 로그인 API를 호출한다
# @then 401을 반환한다
@pytest.mark.skip(reason="skeleton")
def test_expired_token_returns_401():
    pass
```

## 골격에 넣지 않는 것

- assertion, fixture, mock handler, selector·locator, 제품 코드 import, 테스트 helper
- 구현 전에는 알 수 없는 내부 구조(함수명, 컴포넌트명, DOM 구조)
- 스펙에 없는 요구·수치·자동 복구·권한·성능 기준

## 파일 배치

- 프로젝트의 기존 테스트 위치·명명 관례와 계획 지시서가 정한 경로를 따른다.
- runner나 경로를 어디서도 확인할 수 없으면 새 test infrastructure를 만들지 않고 `BLOCKED`로 반환한다.
- 지시서의 runner가 현재 프로젝트에 설치돼 있지 않으면 골격은 쓰되, runner 설치를 구현 단계의 선행 조건으로 계획에 기록한다.

## 변경 규칙

- 스펙이 바뀌면 영향받은 case의 서술과 `@spec` 연결을 갱신하고 전체 검토를 다시 한다.
- 계획의 파일 분류만 바뀌면 골자를 유지한 채 파일을 옮길 수 있다(골자 digest는 파일 경로를 포함하지 않는다).
- 문구 정리는 given·when·then의 의미를 바꾸지 않을 때만 허용한다. 구현 편의로 기대 결과를 완화하는 것은 금지한다.
