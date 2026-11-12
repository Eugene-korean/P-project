#!/usr/bin/env python3
"""
configs/ 아래 조건 파일(*.json)을 전부 읽어 docs/CONDITIONS.md 표로 정리한다.
조건의 원본은 JSON이고, 이 문서는 자동 생성물이다 (손으로 고치지 않는다).

main에 configs/**.json이 push되면 GitHub 서버(.github/workflows/conditions.yml)가
이 스크립트를 돌려 자동 커밋한다. 손으로 돌려도 된다:
  python3 scripts/list_configs.py            # docs/CONDITIONS.md 다시 쓰기
  python3 scripts/list_configs.py --stdout   # 화면에만 출력
"""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIGS = REPO / "configs"
OUT = REPO / "docs/CONDITIONS.md"

def cell(v):
    s = "" if v is None else str(v)
    return s.replace("|", "\\|").replace("~", "\\~").replace("\n", " ")


def count_lengths(v):
    return len([x for x in str(v).split(",") if x.strip()]) if v else 0


def models_of(v):
    return 2 if v == "both" else 1


def describe(path):
    cfg = json.loads(path.read_text(encoding="utf-8"))
    common = cfg.get("common", {})
    rows, total = [], 0
    for c in cfg.get("conditions", []):
        a = dict(common, **c.get("args", {}))
        own = c.get("args", {})                      # 이 조건에서만 바꾼 값 (공통 설정은 위에 따로)
        diff = ", ".join(f"{k}={v}" for k, v in own.items()
                         if k not in ("lengths", "model", "repeats") and v not in (None, "", False))
        n = 0 if a.get("idle_only") else \
            models_of(a.get("model", "qwen")) * count_lengths(a.get("lengths")) * int(a.get("repeats", 5) or 0)
        total += n
        rows.append({"name": c.get("name", ""), "group": c.get("group", ""), "lengths": a.get("lengths", ""),
                     "model": a.get("model", ""), "repeats": a.get("repeats", ""), "limits": diff or "(공통 설정 그대로)",
                     "n": n})
    return cfg, common, rows, total


def build():
    files = sorted(CONFIGS.rglob("*.json"))
    out = ["# 실험 조건 목록", "",
           "> 자동 생성 문서. `configs/` 아래 JSON에서 만들어진다. 고치려면 JSON을 고치고 push한다.",
           "> main에 `configs/**.json`을 push하면 공용 PC에서 그 파일이 자동 실행되고, 이 문서도 다시 만들어진다.",
           "", "## 요약", "",
           "| 파일 | stage | 제목 | 조건 수 | 측정 횟수 |", "| --- | --- | --- | --- | --- |"]
    details, errors = [], []
    for f in files:
        rel = f.relative_to(REPO).as_posix()
        try:
            cfg, common, rows, total = describe(f)
        except Exception as e:                       # 형식 오류 파일도 목록에 남긴다
            errors.append(f"| `{rel}` | 읽기 실패: {cell(e)} |")
            continue
        out.append(f"| `{rel}` | {cell(cfg.get('stage'))} | {cell(cfg.get('title'))} | {len(rows)} | {total:,} |")
        d = [f"### `{rel}`", ""]
        if cfg.get("purpose"):
            d += [f"목적: {cfg['purpose']}", ""]
        com = ", ".join(f"{k}={v}" for k, v in common.items())
        d += [f"공통 설정: {cell(com) or '없음'}", "",
              "| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
        for r in rows:
            d.append(f"| {cell(r['name'])} | {cell(r['group'])} | {cell(r['model'])} | {cell(r['lengths'])} | "
                     f"{cell(r['repeats'])} | {cell(r['limits'])} | {r['n']:,} |")
        for k in ("note", "ctx_note"):
            if cfg.get(k):
                d += ["", f"참고: {cfg[k]}"]
        details += d + [""]
    if errors:
        out += ["", "## 읽지 못한 파일", "", "| 파일 | 이유 |", "| --- | --- |"] + errors
    out += ["", "측정 횟수 = 모델 수 × 길이 개수 × 반복. 한 번 측정할 때마다 재계산, 저장, 복원(cold·warm, RAW·LZ4 설정대로)을 모두 잰다.",
            "", "## 파일별 조건", ""] + details
    return "\n".join(out).rstrip() + "\n"


def main():
    p = argparse.ArgumentParser(description="configs/*.json → docs/CONDITIONS.md")
    p.add_argument("--stdout", action="store_true", help="파일로 쓰지 않고 화면에 출력")
    a = p.parse_args()
    text = build()
    if a.stdout:
        sys.stdout.write(text)
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    if old != text:
        OUT.write_text(text, encoding="utf-8")
        print(f"갱신: {OUT.relative_to(REPO)}")
    else:
        print("변경 없음")


if __name__ == "__main__":
    main()
