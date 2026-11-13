#!/usr/bin/env python3
"""
configs/ 아래 조건 파일(*.json)을 읽어 docs/conditions/에 정리 문서를 만든다.
조건의 원본은 JSON이고, 이 문서들은 자동 생성물이다 (손으로 고치지 않는다).

  docs/conditions/README.md      전체 요약표 (조건 파일 하나당 한 줄)
  docs/conditions/<phase>.md     phase(=configs/ 아래 폴더)별 상세

configs/_로 시작하는 폴더(예: configs/_archive/)는 보관용이라 문서에서 뺀다.
더 이상 없는 phase의 상세 문서는 지운다.

main에 configs/**.json이 push되면 GitHub 서버(.github/workflows/conditions.yml)가
이 스크립트를 돌려 자동 커밋한다. 손으로 돌려도 된다:
  python3 scripts/list_configs.py            # docs/conditions/ 다시 쓰기
  python3 scripts/list_configs.py --stdout   # 요약표만 화면에 출력
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIGS = REPO / "configs"
OUT = REPO / "docs/conditions"
NOTE = ("> 자동 생성 문서. `configs/` 아래 JSON에서 만들어진다. 고치려면 JSON을 고치고 push한다.\n"
        "> main에 `configs/**.json`을 push하면 공용 PC에서 그 파일이 자동 실행되고, 이 문서도 다시 만들어진다.\n")


def cell(v):
    s = "" if v is None else str(v)
    return s.replace("|", "\\|").replace("~", "\\~").replace("\n", " ")


def count_lengths(v):
    return len([x for x in str(v).split(",") if x.strip()]) if v else 0


def models_of(v):
    return 2 if v == "both" else 1


def phase_of(path):
    """configs/phase3/D1.json → phase3, configs/x.json → misc"""
    rel = path.relative_to(CONFIGS)
    return rel.parts[0] if len(rel.parts) > 1 else "misc"


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
                     "model": a.get("model", ""), "repeats": a.get("repeats", ""),
                     "limits": diff or "(공통 설정 그대로)", "n": n})
    return cfg, common, rows, total


def detail(rel, cfg, common, rows):
    d = [f"## `{rel}`", ""]
    if cfg.get("title"):
        d += [f"제목: {cfg['title']}", ""]
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
    return d + [""]


def build():
    """→ {파일 이름: 내용}"""
    files = sorted(p for p in CONFIGS.rglob("*.json")
                   if not any(part.startswith("_") for part in p.relative_to(CONFIGS).parts))
    summary = ["# 실험 조건 목록", "", NOTE,
               "phase 이름을 누르면 조건별 상세가 나온다. "
               "측정 횟수 = 모델 수 × 길이 개수 × 반복 (한 번마다 재계산·저장·복원을 모두 잰다).", "",
               "| phase | 파일 | stage | 제목 | 조건 수 | 측정 횟수 |",
               "| --- | --- | --- | --- | --- | --- |"]
    phases, errors = defaultdict(list), []
    for f in files:
        rel = f.relative_to(REPO).as_posix()
        ph = phase_of(f)
        try:
            cfg, common, rows, total = describe(f)
        except Exception as e:                       # 형식 오류 파일도 목록에 남긴다
            errors.append(f"| `{rel}` | 읽기 실패: {cell(e)} |")
            continue
        summary.append(f"| [{ph}]({ph}.md) | `{rel}` | {cell(cfg.get('stage'))} | {cell(cfg.get('title'))} | "
                       f"{len(rows)} | {total:,} |")
        phases[ph] += detail(rel, cfg, common, rows)
    if errors:
        summary += ["", "## 읽지 못한 파일", "", "| 파일 | 이유 |", "| --- | --- |"] + errors
    out = {"README.md": "\n".join(summary).rstrip() + "\n"}
    for ph, body in phases.items():
        head = [f"# {ph} 조건", "", NOTE, "[← 전체 목록](README.md)", ""]
        out[f"{ph}.md"] = "\n".join(head + body).rstrip() + "\n"
    return out


def main():
    p = argparse.ArgumentParser(description="configs/*.json → docs/conditions/")
    p.add_argument("--stdout", action="store_true", help="파일로 쓰지 않고 요약표만 화면에 출력")
    a = p.parse_args()
    docs = build()
    if a.stdout:
        sys.stdout.write(docs["README.md"])
        return
    OUT.mkdir(parents=True, exist_ok=True)
    changed = []
    for name, text in docs.items():
        f = OUT / name
        if not f.exists() or f.read_text(encoding="utf-8") != text:
            f.write_text(text, encoding="utf-8")
            changed.append(name)
    for f in OUT.glob("*.md"):                       # 없어진 phase의 상세 문서 지우기
        if f.name not in docs:
            f.unlink()
            changed.append(f"{f.name} (삭제)")
    print("갱신: " + ", ".join(changed) if changed else "변경 없음")


if __name__ == "__main__":
    main()
