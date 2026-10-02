#!/usr/bin/env python3
"""스펙 문서가 템플릿 규칙을 지켰는지 기계적으로 검사한다. 의존성 없음.

사용법: python3 check-spec.py <스펙 파일>
종료 코드: 0 = 통과(경고는 있을 수 있음), 1 = 위반 있음, 2 = 사용 오류
경고(휴리스틱)는 stdout에 `경고`로 출력하며 종료 코드에 영향을 주지 않는다.
"""
import re
import sys

SECTIONS = [
    "1. 목표",
    "2. 비목표",
    "3. 완료의 정의",
    "4. 인터페이스 계약",
    "5. 엣지 케이스와 실패 시나리오",
    "미결정 사항",
]
STATUSES = {"초안", "확정", "구현중", "완료"}
SOURCE = re.compile(r"\[(사용자 결정|제안 후 승인)\]")
HEDGE = re.compile(r"할 예정|할 것으로 보인다|할 수도 있다|하면 좋겠다")
SUBHEAD = re.compile(r"^###\s+(\d+\.\d+)\b")
SECREF = re.compile(r"§\s*(\d+\.\d+)")
ECREF = re.compile(r"\bEC-\d+\b")
MULTI = re.compile(r"하고|하며|되고|되며")
MULTI_LIMIT = 3


def main(path):
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        print(f"읽을 수 없음: {e}", file=sys.stderr)
        return 2

    errors = []
    warnings = []
    lines = text.splitlines()

    if not lines or not re.match(r"# 스펙: \S", lines[0]):
        errors.append("첫 줄이 `# 스펙: <기능 이름>` 형식이 아니다")

    m = re.search(r"^- 상태: (.+)$", text, re.M)
    if not m or m.group(1).strip() not in STATUSES:
        errors.append(f"`- 상태:` 값이 {sorted(STATUSES)} 중 하나가 아니다")
    if not re.search(r"^- 최종 갱신: \d{4}-\d{2}-\d{2}\s*$", text, re.M):
        errors.append("`- 최종 갱신:`이 YYYY-MM-DD 형식이 아니다")

    # 섹션 분리 (순서 포함)
    heads = [(i, l[3:].strip()) for i, l in enumerate(lines) if l.startswith("## ")]
    names = [h for _, h in heads]
    if names != SECTIONS:
        errors.append(f"섹션 이름·순서가 템플릿과 다르다. 기대: {SECTIONS} / 실제: {names}")
        return report(errors, warnings)

    body = {}
    for idx, (start, name) in enumerate(heads):
        end = heads[idx + 1][0] if idx + 1 < len(heads) else len(lines)
        body[name] = [l for l in lines[start + 1 : end] if l.strip()]

    for name in SECTIONS:
        if not body[name]:
            errors.append(f"[{name}] 내용이 비어 있다")

    bullet = lambda l: re.match(r"\s*[-*] ", l)

    # 출처 표기: 목록 항목마다, 목표는 문단에 한 번 이상
    for name in SECTIONS[1:5]:
        for l in body[name]:
            if bullet(l) and not SOURCE.search(l):
                errors.append(f"[{name}] 출처 표기([사용자 결정]|[제안 후 승인]) 없음: {l.strip()[:60]}")
    if body["1. 목표"] and not any(SOURCE.search(l) for l in body["1. 목표"]):
        errors.append("[1. 목표] 출처 표기가 없다")

    # 비목표 최소 1개
    if not any(bullet(l) for l in body["2. 비목표"]):
        errors.append("[2. 비목표] 목록 항목이 1개 이상 있어야 한다")

    # 완료의 정의·엣지 케이스: 항목마다 검증 방법
    items = [l for l in body["3. 완료의 정의"] if bullet(l)]
    if not items:
        errors.append("[3. 완료의 정의] 목록 항목이 없다")
    for name in ("3. 완료의 정의", "5. 엣지 케이스와 실패 시나리오"):
        for l in body[name]:
            if bullet(l) and not re.search(r"검증\s*:", l):
                errors.append(f"[{name}] 검증 방법(`— 검증:`)이 없다: {l.strip()[:60]}")

    # 항목 ID: 완료의 정의는 DoD-N, 엣지 케이스는 EC-N. 중복 금지(테스트 골격이 이 ID로 항목을 잇는다)
    for name, prefix in (("3. 완료의 정의", "DoD"), ("5. 엣지 케이스와 실패 시나리오", "EC")):
        seen = set()
        for l in body[name]:
            if not bullet(l):
                continue
            m = re.match(r"\s*[-*] (%s-\d+): " % prefix, l)
            if not m:
                errors.append(f"[{name}] 항목이 `{prefix}-N: ` ID로 시작하지 않는다: {l.strip()[:60]}")
            elif m.group(1) in seen:
                errors.append(f"[{name}] ID 중복: {m.group(1)}")
            else:
                seen.add(m.group(1))

    # 참조 무결성: DoD/EC가 가리키는 §N.M, EC-N이 실제로 있어야 한다
    subheads = {m.group(1) for l in lines if (m := SUBHEAD.match(l))}
    ec_ids = set()
    for l in body["5. 엣지 케이스와 실패 시나리오"]:
        m = re.match(r"\s*[-*] (EC-\d+): ", l)
        if m:
            ec_ids.add(m.group(1))
    for name in ("3. 완료의 정의", "5. 엣지 케이스와 실패 시나리오"):
        for l in body[name]:
            if not bullet(l):
                continue
            if subheads:  # 소제목이 없는 스펙은 §N.M 검사를 건너뛴다
                for ref in SECREF.findall(l):
                    if ref not in subheads:
                        errors.append(f"[{name}] 존재하지 않는 소제목 §{ref} 참조: {l.strip()[:60]}")
            for ref in ECREF.findall(l):
                if ref not in ec_ids:
                    errors.append(f"[{name}] 존재하지 않는 {ref} 참조: {l.strip()[:60]}")

    # 한 항목에 결과가 여러 개 섞였는지 (경고만; 단순 휴리스틱)
    for name in ("3. 완료의 정의", "5. 엣지 케이스와 실패 시나리오"):
        for l in body[name]:
            if bullet(l):
                claim = re.split(r"—\s*검증", l)[0]
                n = len(MULTI.findall(claim))
                if n >= MULTI_LIMIT:
                    warnings.append(f"[{name}] 결과가 여러 개 섞였을 수 있다(연결어 {n}회, 항목 분리 검토): {l.strip()[:60]}")

    # 템플릿 placeholder 잔존
    for i, l in enumerate(lines, 1):
        if re.search(r"<[^<>\n]{1,40}>", l) and not l.startswith("```"):
            errors.append(f"{i}행: 템플릿 placeholder가 남아 있다: {l.strip()[:60]}")

    # 템플릿 안내 주석 잔존
    for i, l in enumerate(lines, 1):
        if "<!--" in l:
            errors.append(f"{i}행: 템플릿 안내 주석(<!-- -->)이 남아 있다: {l.strip()[:60]}")

    # 유보 표현
    for i, l in enumerate(lines, 1):
        if HEDGE.search(l):
            errors.append(f"{i}행: 유보 표현은 확정 문체(`~한다`)로 바꾼다: {l.strip()[:60]}")

    return report(errors, warnings)


def report(errors, warnings=()):
    if warnings:
        print(f"경고 {len(warnings)}건 (통과 여부에는 영향 없음)")
        for w in warnings:
            print(f"- {w}")
    if errors:
        print(f"위반 {len(errors)}건")
        for e in errors:
            print(f"- {e}")
        return 1
    print("통과: 템플릿 규칙 위반 없음 (내용의 옳고 그름은 검사하지 않는다)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
