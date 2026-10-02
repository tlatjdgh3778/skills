#!/usr/bin/env python3
"""테스트 골격이 스펙의 항목(DoD-N, EC-N)을 빠짐없이 잇고 있는지 기계적으로 검사한다. 의존성 없음.

언어와 무관하다. 각 case 직전의 태그 주석(`@spec`, `@given`, `@when`, `@then`)만 읽는다.
`@then`은 한 case에 여러 줄 올 수 있다(digest에는 입력 순서대로 " ; "로 이은 한 문자열로 반영). 나머지 태그는 한 줄이다.
의미의 옳고 그름은 검사하지 않는다(그것은 새 reviewer의 일이다).

사용법:
  check-skeleton.py --spec <스펙> --files <파일>... [--exempt DoD-3,EC-2]
      골격 검사. 통과하면 골자 digest를 출력한다.
  check-skeleton.py --spec <스펙> --files <파일>... --frozen <digest>
      동결 확인. 태그 내용의 digest만 비교한다(본문이 채워졌어도 골자가 그대로인지 본다).
종료 코드: 0 = 통과, 1 = 위반 있음, 2 = 사용 오류
"""
import argparse
import hashlib
import re
import sys

ID = re.compile(r"^(DoD|EC)-\d+$")
SPEC_ITEM = re.compile(r"^\s*[-*] ((?:DoD|EC)-\d+): ")
# 주석 접두(`/**`, `*`, `//`, `#`, `"""`, `--` …)를 걷어 내고 태그를 읽는다.
TAG = re.compile(
    r"^\s*(?:/\*+|\*+/?|//+|#+|\"\"\"|'''|--)?\s*@(spec|given|when|then)\b[ \t]*(.*?)\s*(?:\*/|\"\"\"|''')?\s*$"
)
COMMENT_ONLY = re.compile(r"^\s*(?:/\*+|\*+/?|//+|#+|\"\"\"|'''|--)?\s*$")
COMMENT_LINE = re.compile(r"^\s*(?:/\*|\*|//|#(?!\[|!\[)|\"\"\"|'''|--)")  # `#[`·`#![`는 Rust 속성(코드)이다
# 골격에 있어서는 안 되는 assertion의 흔한 형태(휴리스틱)
ASSERTION = re.compile(
    r"\b(expect|assert\w*|assertThat|should)\s*[(.]|\.(toBe|toEqual|toHave\w*|toMatch\w*|toContain\w*|toThrow\w*)\b|\bself\.assert\w+"
)
PENDING = re.compile(r"todo|fixme|skip|disabled|pending|ignore|unimplemented|notimplemented|\bxit\b|\bxtest\b", re.I)


def spec_ids(path):
    ids, in_sec = [], False
    for line in open(path, encoding="utf-8").read().splitlines():
        if line.startswith("## "):
            in_sec = line[3:].strip() in ("3. 완료의 정의", "5. 엣지 케이스와 실패 시나리오")
        elif in_sec:
            m = SPEC_ITEM.match(line)
            if m:
                ids.append(m.group(1))
    return ids


def parse(path, errors):
    """파일에서 case 블록 목록을 읽는다. 블록 = {ids, given, when, then, line, window}.
    window는 블록 뒤 코드 4줄로, 미구현 표기(todo·fixme·skip 등)를 거기서 찾는다."""
    blocks, cur = [], None
    lines = open(path, encoding="utf-8").read().splitlines()
    for n, line in enumerate(lines, 1):
        m = TAG.match(line)
        if m:
            tag, text = m.group(1), m.group(2)
            if tag == "spec":
                cur = {"ids": text.split(), "given": "", "when": "", "then": "", "line": n}
                blocks.append(cur)
            elif cur is None:
                errors.append(f"{path}:{n}: `@{tag}`가 `@spec` 블록 밖에 있다")
            elif tag == "then":
                # 같은 요청·상태에서 관찰되는 결과는 `@then`을 여러 줄로 쓴다. 입력 순서대로 " ; "로 잇는다.
                if text:
                    cur["then"] = cur["then"] + " ; " + text if cur["then"] else text
            elif cur[tag]:
                errors.append(f"{path}:{n}: `@{tag}`가 한 블록에 두 번 나온다")
            else:
                cur[tag] = text
            continue
        if cur is not None and (COMMENT_ONLY.match(line) or COMMENT_LINE.match(line)):
            continue
        if cur is not None:
            cur["window"] = " ".join(l.strip() for l in lines[n - 1 : n + 3])
            cur = None
    return blocks


def digest(blocks):
    norm = sorted(
        "|".join([",".join(sorted(b["ids"])), b["given"], b["when"], b["then"]]) for b in blocks
    )
    return hashlib.sha256("\n".join(norm).encode("utf-8")).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--files", nargs="+", required=True)
    ap.add_argument("--exempt", default="", help="테스트로 덮지 않는 항목 ID(쉼표). 사유는 계획 파일에 기록한다")
    ap.add_argument("--frozen", help="계획 파일에 기록된 골자 digest. 주어지면 digest만 비교한다")
    a = ap.parse_args()

    try:
        ids = spec_ids(a.spec)
    except OSError as e:
        print(f"스펙을 읽을 수 없음: {e}", file=sys.stderr)
        return 2
    if not ids:
        print("스펙에서 DoD-N/EC-N 항목을 찾지 못했다. spec 스킬의 ID 규칙을 확인한다", file=sys.stderr)
        return 2

    errors, blocks = [], []
    for f in a.files:
        try:
            blocks += [dict(b, file=f) for b in parse(f, errors)]
        except OSError as e:
            print(f"골격 파일을 읽을 수 없음: {e}", file=sys.stderr)
            return 2

    d = digest(blocks)

    if a.frozen:
        if d == a.frozen:
            print(f"동결 유지: 골자 digest 일치 ({d}), case {len(blocks)}개")
            return 0
        print(f"골자 변경 감지: 기록 {a.frozen} / 현재 {d}")
        print("- 태그(@spec/@given/@when/@then)의 내용이 바뀌었거나 case가 추가·삭제됐다. 스펙 변경 없이 골자가 바뀌는 것은 허용되지 않는다")
        return 1

    exempt = {x for x in (s.strip() for s in a.exempt.split(",")) if x}
    for x in sorted(exempt - set(ids)):
        errors.append(f"--exempt의 {x}가 스펙에 없다")

    covered = set()
    for b in blocks:
        where = f"{b['file']}:{b['line']}"
        if not b["ids"]:
            errors.append(f"{where}: `@spec`에 항목 ID가 없다")
        for i in b["ids"]:
            if not ID.match(i):
                errors.append(f"{where}: 형식이 잘못된 ID `{i}` (DoD-N 또는 EC-N)")
            elif i not in ids:
                errors.append(f"{where}: 스펙에 없는 ID `{i}`")
            else:
                covered.add(i)
        for t in ("given", "when", "then"):
            if not b[t]:
                errors.append(f"{where}: `@{t}`가 없거나 비어 있다")
        if "window" in b and not PENDING.search(b["window"]):
            errors.append(f"{where}: case에 미구현 표기(todo·fixme·skip 등)가 없다 — 골격은 통과로 세지 않도록 표기한다: {b['window'][:60]}")

    for i in ids:
        if i not in covered and i not in exempt:
            errors.append(f"{i}를 잇는 case가 없다 (테스트로 덮지 않는다면 --exempt와 사유 기록이 필요하다)")
    for i in sorted(exempt & covered):
        errors.append(f"{i}는 제외로 지정됐는데 case가 있다. 둘 중 하나로 정리한다")

    # 골격에 assertion이 섞였는지(주석이 아닌 줄만)
    for f in a.files:
        for n, line in enumerate(open(f, encoding="utf-8").read().splitlines(), 1):
            if not COMMENT_LINE.match(line) and ASSERTION.search(line):
                errors.append(f"{f}:{n}: assertion으로 보이는 코드가 있다. 골격에는 본문을 쓰지 않는다: {line.strip()[:60]}")

    if errors:
        print(f"위반 {len(errors)}건")
        for e in errors:
            print(f"- {e}")
        return 1
    print(f"통과: 항목 {len(ids)}개 중 case 연결 {len(covered)}개, 제외 {len(exempt)}개, case {len(blocks)}개")
    print(f"골자 digest: {d}")
    print("(형식만 본다. case가 항목의 의미를 약화하지 않는지는 검사하지 않는다)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
