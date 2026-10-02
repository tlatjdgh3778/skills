#!/usr/bin/env python3
"""계획 파일이 템플릿 규칙을 지켰는지, 스펙과 어긋나지 않는지 기계적으로 검사한다. 의존성 없음.

검사하는 것: 구조, Task 필드, 선행 참조와 순환, 연결 항목(DoD-N·EC-N)과 coverage,
병렬 Task의 수정 파일 겹침, 스펙 원문 복사. 계획이 옳은지는 검사하지 않는다.

사용법: python3 check-plan.py <계획 파일> --spec <스펙 파일>
종료 코드: 0 = 통과, 1 = 위반 있음, 2 = 사용 오류
"""
import argparse
import re
import sys

SECTIONS = ["1. 구현 전략", "2. Task", "3. 항목 coverage", "4. 실행 순서", "5. 차단 사항", "테스트 설계 증거"]
PLAN_STATUS = {"초안", "승인"}
TASK_STATUS = {"대기", "진행", "검증대기", "완료", "차단"}
FIELDS = ["사이드", "상태", "목적", "선행", "연결 항목", "수정 대상", "따라야 할 패턴", "완료 조건",
          "실행 명령", "수정 금지", "테스트 파일·runner", "mock 허용 경계", "데이터 격리", "실행 환경"]
REQUIRED = ["사이드", "상태", "목적", "선행", "연결 항목", "수정 대상", "완료 조건", "실행 명령"]
TEST_REQUIRED = ["테스트 파일·runner", "mock 허용 경계", "데이터 격리"]
FIELD_RE = re.compile(r"^- (%s): ?(.*)$" % "|".join(re.escape(f) for f in FIELDS))
TASK_RE = re.compile(r"^### (T-\d+) — (\S.*)$")
ITEM = re.compile(r"\b((?:DoD|EC)-\d+)\b")
SPEC_ITEM = re.compile(r"^\s*[-*] ((?:DoD|EC)-\d+): ")
MIN_COPY = 40  # 이 길이 이상의 스펙 문장이 계획에 그대로 있으면 복사로 본다


def norm(line):
    """비교용 정규화: 목록 기호, 항목 ID, 필드 이름, 출처 태그, 공백을 걷어 낸다."""
    s = line.strip()
    s = re.sub(r"^[-*] ", "", s)
    s = re.sub(r"^\*\*?[^*]+\*\*?:?\s*", "", s) if s.startswith("**") else s
    s = re.sub(r"^(?:DoD|EC)-\d+: ", "", s)
    s = re.sub(r"^(%s): ?" % "|".join(re.escape(f) for f in FIELDS), "", s)
    s = re.sub(r"\s*\[(?:사용자 결정|제안 후 승인)\]\s*$", "", s)
    s = re.sub(r"\s*— 검증: .*$", "", s)
    return re.sub(r"\s+", " ", s).strip()


def read_spec(path):
    ids, copy_src, sec = [], [], None
    for line in open(path, encoding="utf-8").read().splitlines():
        if line.startswith("## "):
            sec = line[3:].strip()
            continue
        if sec in ("3. 완료의 정의", "5. 엣지 케이스와 실패 시나리오"):
            m = SPEC_ITEM.match(line)
            if m:
                ids.append(m.group(1))
        if sec in ("1. 목표", "3. 완료의 정의", "4. 인터페이스 계약", "5. 엣지 케이스와 실패 시나리오"):
            n = norm(line)
            if len(n) >= MIN_COPY:
                copy_src.append(n)
    return ids, copy_src


def parse(text):
    """(헤더 dict, 섹션별 줄, Task 목록)을 돌려준다."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    lines = text.splitlines()
    header, sections, cur = {}, {}, None
    tasks, task = [], None
    for n, line in enumerate(lines, 1):
        if line.startswith("## "):
            cur = line[3:].strip()
            sections[cur] = []
            task = None
            continue
        if cur is None:
            m = re.match(r"^- (상태|스펙|기준 코드|최종 갱신): (.+)$", line)
            if m:
                header[m.group(1)] = m.group(2).strip()
            continue
        sections[cur].append((n, line))
        if cur == "2. Task":
            m = TASK_RE.match(line)
            if m:
                task = {"id": m.group(1), "name": m.group(2), "line": n, "f": {}}
                tasks.append(task)
                continue
            m = FIELD_RE.match(line)
            if m and task is not None:
                task["f"][m.group(1)] = m.group(2).strip()
    return header, sections, tasks, lines


def paths(value):
    return [p.rstrip("/") for p in re.findall(r"`([^`]+)`", value)]


def overlap(a, b):
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--spec", required=True)
    a = ap.parse_args()
    try:
        text = open(a.plan, encoding="utf-8").read()
        spec_ids, copy_src = read_spec(a.spec)
    except OSError as e:
        print(f"읽을 수 없음: {e}", file=sys.stderr)
        return 2
    if not spec_ids:
        print("스펙에서 DoD-N/EC-N 항목을 찾지 못했다. spec 스킬의 ID 규칙을 확인한다", file=sys.stderr)
        return 2

    errors = []
    header, sections, tasks, lines = parse(text)

    if not lines or not re.match(r"# 계획: \S", lines[0]):
        errors.append("첫 줄이 `# 계획: <기능 이름>` 형식이 아니다")
    if header.get("상태") not in PLAN_STATUS:
        errors.append(f"`- 상태:`가 {sorted(PLAN_STATUS)} 중 하나가 아니다")
    if "스펙" not in header:
        errors.append("`- 스펙:` 경로가 없다")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", header.get("최종 갱신", "")):
        errors.append("`- 최종 갱신:`이 YYYY-MM-DD 형식이 아니다")

    names = list(sections)
    if names != SECTIONS:
        errors.append(f"섹션 이름·순서가 템플릿과 다르다. 기대: {SECTIONS} / 실제: {names}")
        return report(errors)
    for name in SECTIONS:
        if not any(l.strip() for _, l in sections[name]):
            errors.append(f"[{name}] 내용이 비어 있다")

    # Task
    if not tasks:
        errors.append("[2. Task] Task가 없다")
    ids = [t["id"] for t in tasks]
    for i in sorted({i for i in ids if ids.count(i) > 1}):
        errors.append(f"Task ID 중복: {i}")
    by_id = {t["id"]: t for t in tasks}

    deps, links = {}, {}
    for t in tasks:
        f, where = t["f"], f"{t['id']}(L{t['line']})"
        for r in REQUIRED:
            if not f.get(r):
                errors.append(f"{where}: 필드 `{r}`가 없거나 비어 있다")
        if f.get("상태") and f["상태"] not in TASK_STATUS:
            errors.append(f"{where}: `상태`가 {sorted(TASK_STATUS)} 중 하나가 아니다: {f['상태']}")
        side = f.get("사이드", "")
        is_test = "테스트" in side or "e2e" in side.lower()
        if is_test:
            for r in TEST_REQUIRED + (["실행 환경"] if "e2e" in side.lower() else []):
                if not f.get(r):
                    errors.append(f"{where}: 테스트 Task는 `{r}`가 필요하다")
        pre = f.get("선행", "")
        deps[t["id"]] = [] if pre in ("", "없음") else re.findall(r"T-\d+", pre)
        for d in deps[t["id"]]:
            if d not in by_id:
                errors.append(f"{where}: 선행 `{d}`가 없다")
            elif d == t["id"]:
                errors.append(f"{where}: 자기 자신을 선행으로 지정했다")
        links[t["id"]] = set(ITEM.findall(f.get("연결 항목", "")))
        for i in sorted(links[t["id"]] - set(spec_ids)):
            errors.append(f"{where}: 연결 항목 `{i}`가 스펙에 없다")
        if f.get("연결 항목") and not links[t["id"]]:
            errors.append(f"{where}: `연결 항목`에 DoD-N·EC-N이 없다")

    # 순환
    state = {}
    def visit(n, stack):
        if state.get(n) == 2:
            return
        if state.get(n) == 1:
            errors.append("선행 순환: " + " → ".join(stack[stack.index(n):] + [n]))
            return
        state[n] = 1
        for d in deps.get(n, []):
            if d in by_id:
                visit(d, stack + [n])
        state[n] = 2
    for n in ids:
        visit(n, [])

    # 병렬(선행 관계가 없는 쌍)의 수정 파일 겹침
    anc = {}
    def ancestors(n, seen=()):
        if n in anc:
            return anc[n]
        out = set()
        for d in deps.get(n, []):
            if d in by_id and d not in seen:
                out |= {d} | ancestors(d, seen + (n,))
        anc[n] = out
        return out
    for i, x in enumerate(ids):
        for y in ids[i + 1:]:
            if y in ancestors(x) or x in ancestors(y):
                continue
            for p in paths(by_id[x]["f"].get("수정 대상", "")):
                for q in paths(by_id[y]["f"].get("수정 대상", "")):
                    if overlap(p, q):
                        errors.append(f"병렬 Task {x}·{y}가 같은 파일을 수정한다: `{p}` / `{q}` (한 Task에 합치거나 선행으로 순차화)")

    # coverage
    cov, excluded = {}, {}
    for n, line in sections["3. 항목 coverage"]:
        m = re.match(r"^- ((?:DoD|EC)-\d+): (.+)$", line)
        if not m:
            if line.strip() and not line.strip().startswith("-"):
                errors.append(f"L{n}: coverage 줄이 `- DoD-N: T-N, …` 형식이 아니다: {line.strip()[:50]}")
            continue
        item, val = m.group(1), m.group(2).strip()
        if item not in spec_ids:
            errors.append(f"L{n}: coverage의 `{item}`가 스펙에 없다")
        elif val.startswith("제외"):
            if not re.sub(r"^제외\s*[—-]?\s*", "", val):
                errors.append(f"L{n}: `{item}` 제외에는 사유가 필요하다")
            excluded[item] = val
        else:
            cov[item] = set(re.findall(r"T-\d+", val))
    computed = {}
    for tid, its in links.items():
        for i in its:
            computed.setdefault(i, set()).add(tid)
    for i in spec_ids:
        if i in excluded:
            if i in computed:
                errors.append(f"{i}는 coverage에서 제외인데 {sorted(computed[i])}가 연결하고 있다")
        elif i not in computed:
            errors.append(f"{i}를 연결한 Task가 없다 (제외라면 coverage에 `- {i}: 제외 — 사유`)")
        elif cov.get(i) != computed[i]:
            errors.append(f"coverage의 {i}가 Task의 연결 항목과 다르다: 기록 {sorted(cov.get(i, []))} / Task 기준 {sorted(computed[i])}")

    # 스펙 원문 복사 (계획은 ID로 가리키고 원문을 옮기지 않는다)
    body = text
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    for n, line in enumerate(body.splitlines(), 1):
        nl = norm(line)
        if len(nl) < MIN_COPY:
            continue
        for s in copy_src:
            if s in nl:
                errors.append(f"L{n}: 스펙 원문을 복사했다. `연결 항목` ID로 가리킨다: {line.strip()[:60]}")
                break

    # 템플릿 placeholder 잔존
    for n, line in enumerate(body.splitlines(), 1):
        if re.search(r"<[^<>\n]{1,40}>", line):
            errors.append(f"L{n}: 템플릿 placeholder가 남아 있다: {line.strip()[:60]}")

    return report(errors, len(tasks), len(spec_ids))


def report(errors, n_tasks=0, n_items=0):
    if errors:
        print(f"위반 {len(errors)}건")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"통과: Task {n_tasks}개, 스펙 항목 {n_items}개 모두 연결 또는 제외")
    print("(형식·참조·coverage·병렬 충돌·스펙 복사만 본다. 계획의 내용이 옳은지는 검사하지 않는다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
