#!/usr/bin/env python3
"""
2차 실험 분석 (단계 E). sweep_summary.csv(+ 조건별 results.csv, vmstat.log)에서 계산해
<out-root>/analysis/ 에 CSV와 analysis.md(Markdown 표)를 쓴다.

정의 (단위: ms, 토큰, 바이트, MB = 10^6 바이트, MiB = 2^20 바이트)
  s      토큰당 KV 크기 (바이트/토큰). RAW 파일 크기를 길이에 대해 직선 맞춤한 기울기
  r(N)   길이 N에서 Prefill 처리 속도 = N / 재계산 시간 (토큰/s)
  r_fit  길이 1024 이하에서 재계산 시간 = c0 + N/r_fit 직선 맞춤 (N* 계산용)
  B      조건 시작 시 --measure-disk로 잰 kv-dir 읽기 속도 (MB/s)
  T0     16토큰 복원(이어서 시작까지) 시간 − 16토큰 파일 크기 / B
  B*     s × r  : 기본 비용을 무시할 때 로드와 재계산이 같아지는 읽기 속도 (계산값)
  B*_T0  N·s / (재계산(N) − T0) : T0까지 넣은 교차 읽기 속도 (계산값)
  N*     T0 / (1/r_fit − s/B) : 저장·로드가 이득이 되기 시작하는 토큰 수 (계산값)

예시: ~/aiwork/venv/bin/python scripts/analyze_results.py --out-root ~/aiwork/results/phase2
"""

import argparse
import csv
import datetime as dt
import json
import math
from collections import defaultdict
from pathlib import Path

HOME = Path.home()
MB = 1e6
MIB = 1024 ** 2
DEVICE_TIERS = [  # (등급, 설명, 읽기 MB/s) — 계산값 등급
    ("T2 휴대폰 UFS 3.1", 2100.0),
    ("T3 휴대폰 UFS 4.0", 4200.0),
    ("T5 PC NVMe", 7450.0),
]


def f(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def r_(x, nd=2):
    return "" if x is None else round(x, nd)


def linfit(xs, ys):
    n = len(xs)
    if n < 2:
        return None, None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None, None
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return my - b * mx, b       # 절편, 기울기


def interp_cross(points, target=1.0, logx=True):
    """(x, y) 점들을 x 순으로 보고 y가 target을 지나는 x를 (log)선형 보간. 없으면 None."""
    pts = sorted((x, y) for x, y in points if x and y)
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if (y1 - target) * (y2 - target) <= 0 and y1 != y2:
            if logx:
                lx = math.log(x1) + (math.log(target) - math.log(y1)) * \
                     (math.log(x2) - math.log(x1)) / (math.log(y2) - math.log(y1))
                return math.exp(lx)
            return x1 + (target - y1) * (x2 - x1) / (y2 - y1)
    return None


def write_csv(path, rows, fields=None):
    if not rows:
        return
    fields = fields or list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def md_table(rows, cols, headers=None):
    if not rows:
        return "_(데이터 없음)_\n"
    headers = headers or cols
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- 읽기

def load(out_root):
    rows = list(csv.DictReader(open(out_root / "sweep_summary.csv")))
    for r in rows:
        r["N"] = int(r["n_tokens"])
        r["cond"] = f"{r['stage']}/{r['condition']}"
    return rows


def kv_size_per_token(rows):
    """모델별 s: RAW 파일 크기 vs 길이 직선 맞춤."""
    out = {}
    by = defaultdict(dict)
    for r in rows:
        if f(r.get("raw_bytes")):
            by[r["model"]][r["N"]] = f(r["raw_bytes"])
    for m, d in by.items():
        c, s = linfit(list(d), list(d.values()))
        if s is None:                       # 길이가 하나뿐이면 단순 나눗셈
            n, b = next(iter(d.items()))
            c, s = 0.0, b / n
        out[m] = {"model": m, "s_bytes_per_token": round(s, 1), "header_bytes": round(c, 0),
                  "lengths": len(d)}
    return out


def pick(rows, cond, model, cache=None, storage="raw"):
    return [r for r in rows if r["cond"] == cond and r["model"] == model and r["storage"] == storage
            and (cache is None or r["cache"] == cache)]


def main_cache(rs):
    caches = {r["cache"] for r in rs}
    return "cold" if "cold" in caches else ("warm" if "warm" in caches else None)


# ---------------------------------------------------------------- 계산

def per_condition(rows, S):
    """조건 × 모델 단위: r_fit, c0, B, T0, N*(식), N*(실측 교차)."""
    out = []
    keys = sorted({(r["cond"], r["model"]) for r in rows})
    for cond, model in keys:
        allr = pick(rows, cond, model)
        if not allr:
            continue
        cache = main_cache(allr)
        rs = sorted([r for r in allr if r["cache"] == cache], key=lambda r: r["N"])
        s = S.get(model, {}).get("s_bytes_per_token")
        x = rs[0]
        B = f(x.get("disk_read_mb_per_s"))          # 조건 시작 시 실측 (cold면 SSD, RAM 디스크면 RAM)
        if cache == "warm" and x.get("kv_fs") != "tmpfs":
            B = None                                # 페이지 캐시 warm은 디스크 읽기 속도가 아님
        lin = [(r["N"], f(r["recompute_ms_mean"])) for r in rs if r["N"] <= 1024 and f(r["recompute_ms_mean"])]
        c0, slope = linfit([a for a, _ in lin], [b for _, b in lin])
        r_fit = 1000.0 / slope if slope and slope > 0 else None
        r16 = next((r for r in rs if r["N"] == 16), None)
        T0 = None
        if r16 and f(r16["resume_total_ms_mean"]) is not None:
            load_ms = (f(r16["raw_bytes"]) / MB) / B * 1000 if B else 0.0
            T0 = f(r16["resume_total_ms_mean"]) - load_ms
        nstar = nstar_c0 = None
        if T0 is not None and r_fit and s:
            per_tok = 1000.0 / r_fit - ((s / MB) / B * 1000 if B else 0.0)   # ms/토큰
            if per_tok > 0:
                nstar = T0 / per_tok
                nstar_c0 = max(T0 - (c0 or 0), 0) / per_tok
            else:
                nstar = nstar_c0 = math.inf      # 로드가 토큰당 더 비쌈 → 길어질수록 재계산이 유리
        sp = [(r["N"], f(r["speedup_mean"])) for r in rs]
        cross = interp_cross(sp, 1.0, logx=True)
        if cross is not None:
            obs = round(cross, 1)
        elif sp and all(v and v > 1 for _, v in sp):
            obs = f"<{min(n for n, _ in sp)} (모든 길이에서 배율>1)"
        elif sp and all(v and v < 1 for _, v in sp):
            obs = f">{max(n for n, _ in sp)} (모든 길이에서 배율<1)"
        else:
            obs = "미측정"
        sp4096 = next((v for n, v in sp if n == 4096), None)
        out.append({
            "stage": x["stage"], "condition": x["condition"], "model": model, "cache": cache,
            "status": x.get("status", ""), "threads": x.get("threads", ""), "max_freq": x.get("max_freq", ""),
            "io_read": x.get("io_read", ""), "mem_limit": x.get("mem_limit", ""),
            "s_B_per_tok": s, "r_fit_tok_s": r_(r_fit), "c0_ms": r_(c0),
            "B_MB_s": r_(B), "T0_ms": r_(T0),
            "Bstar_MB_s(계산값)": r_(s * r_fit / MB if s and r_fit else None),
            "Nstar_tok(계산값)": r_(nstar, 1) if nstar != math.inf else "∞",
            "Nstar_c0_tok(계산값)": r_(nstar_c0, 1) if nstar_c0 != math.inf else "∞",
            "Nstar_tok(실측 교차)": obs,
            "speedup_4096": r_(sp4096),
            "result_dir": x.get("result_dir", ""),
        })
    return out


def per_length(rows, S, cond_info):
    """조건 × 모델 × 길이: r(N), B*(N), B*_T0(N), 저장 비용, 메모리."""
    T0 = {(c["stage"] + "/" + c["condition"], c["model"]): f(c["T0_ms"]) for c in cond_info}
    out = []
    for r in sorted(rows, key=lambda r: (r["cond"], r["model"], r["storage"], r["cache"], r["N"])):
        if r["storage"] != "raw":
            continue
        s = S.get(r["model"], {}).get("s_bytes_per_token")
        rate = f(r.get("prefill_tok_per_s"))
        rec = f(r["recompute_ms_mean"])
        t0 = T0.get((r["cond"], r["model"]))
        bt0 = None
        if s and rec and t0 is not None and rec > t0:
            bt0 = r["N"] * s / MB / ((rec - t0) / 1000)
        idle = f(r.get("idle_rss_mb"))
        rss = f(r.get("rss_after_prefill_mb_mean"))
        out.append({
            "stage": r["stage"], "condition": r["condition"], "model": r["model"], "cache": r["cache"],
            "n_tokens": r["N"], "recompute_ms": r_(rec), "recompute_ms_std": r_(f(r.get("recompute_ms_std"))),
            "resume_total_ms": r_(f(r["resume_total_ms_mean"])),
            "resume_total_ms_std": r_(f(r.get("resume_total_ms_std"))),
            "speedup": r_(f(r["speedup_mean"])), "all_match": r.get("all_match", ""),
            "r_tok_s": r_(rate), "load_MB_s": r_(f(r.get("load_mb_per_s"))),
            "Bstar_MB_s(계산값)": r_(s * rate / MB if s and rate else None),
            "Bstar_T0_MB_s(계산값)": r_(bt0),
            "save_total_ms": r_(f(r.get("save_total_ms_mean"))),
            "breakeven_reuse": r_(f(r.get("breakeven_reuse")), 3),
            "rss_increase_MiB": r_(rss - idle if rss is not None and idle is not None else None, 1),
            "kv_theory_MiB(계산값)": r_(s * r["N"] / MIB if s else None, 1),
            "swap_after_restore_MiB_max": r.get("swap_after_restore_mb_max", ""),
            "result_dir": r.get("result_dir", ""),
        })
    return out


def d2_crossover(rows, S, length_rows):
    """D2: 길이별로 읽기 속도 B를 바꿔 가며 배율=1이 되는 B(실측 교차)와 예측 B* 비교."""
    d2 = [r for r in rows if r["stage"] == "D2" and r["storage"] == "raw" and r["cache"] == "cold"]
    out = []
    pred = {(x["condition"], x["model"], x["n_tokens"]): x for x in length_rows if x["stage"] == "D2"}
    for model in sorted({r["model"] for r in d2}):
        for N in sorted({r["N"] for r in d2 if r["model"] == model}):
            pts = [(f(r["disk_read_mb_per_s"]), f(r["speedup_mean"])) for r in d2
                   if r["model"] == model and r["N"] == N]
            cross = interp_cross(pts, 1.0, logx=True)
            # 예측: 제한 없는 D2 조건의 r(N)으로 B* = s·r, T0 포함 B*_T0
            p = pred.get(("nolimit", model, N), {})
            bs, bt = f(p.get("Bstar_MB_s(계산값)")), f(p.get("Bstar_T0_MB_s(계산값)"))
            lowB = min(pts) if pts else (None, None)
            obs = r_(cross) if cross is not None else (
                f"<{r_(lowB[0])} (최저 B에서도 배율 {r_(lowB[1])})" if lowB[1] and lowB[1] > 1 else "미측정")
            out.append({
                "model": model, "n_tokens": N,
                "B_cross_MB_s(실측 보간)": obs,
                "Bstar_MB_s(계산값)": r_(bs), "Bstar_T0_MB_s(계산값)": r_(bt),
                "err_Bstar_%": r_((bs - cross) / cross * 100, 1) if cross and bs else "",
                "err_Bstar_T0_%": r_((bt - cross) / cross * 100, 1) if cross and bt else "",
                "speedup_by_B": "; ".join(f"{r_(b, 1)}MB/s→x{r_(s_)}" for b, s_ in sorted(pts) if b),
            })
    return out


def parse_vmstat(path):
    """vmstat -t 1 → [(epoch, {열: 값})]."""
    out, cols = [], None
    try:
        lines = open(path).read().splitlines()
    except Exception:
        return out
    for line in lines:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "r" and "si" in parts:
            cols = parts
            continue
        if cols is None or not parts[0].isdigit():
            continue
        try:
            ts = dt.datetime.strptime(" ".join(parts[-2:]), "%Y-%m-%d %H:%M:%S").timestamp()
            vals = dict(zip(cols, map(int, parts[:len(cols) - 1])))
            out.append((ts, vals))
        except Exception:
            continue
    return out


def d4_pressure(rows, length_rows):
    """D4: 메모리 상한별 길이마다 재계산·복원 시간 변화와 swap(si/so, VmSwap)."""
    out = []
    d4 = [r for r in rows if r["stage"] == "D4" and r["storage"] == "raw"]
    for r in sorted(d4, key=lambda r: (r["model"], r["condition"], r["N"])):
        rd = Path(r.get("result_dir", ""))
        vm = parse_vmstat(rd / "vmstat.log")
        si = so = 0
        # 각 측정 줄의 구간 = 앞 줄의 t_end ~ 이 줄의 t_end (재계산·저장·복원을 모두 포함, 겹치지 않음)
        wins, prev = [], None
        try:
            for x in csv.DictReader(open(rd / "results.csv")):
                a, b = f(x["t_start"]), f(x["t_end"])
                lo = prev if (prev is not None and x["model"] == prev_model) else (a or 0) - 60
                if x["model"] == r["model"] and int(x["n_tokens"]) == r["N"] and b:
                    wins.append((lo, b))
                prev, prev_model = b, x["model"]
        except Exception:
            wins = []
        for ts, v in vm:
            if any(lo < ts <= hi for lo, hi in wins):
                si += v.get("si", 0)
                so += v.get("so", 0)
        out.append({
            "model": r["model"], "condition": r["condition"], "mem_limit": r.get("mem_limit") or "없음",
            "status": r.get("status", ""), "n_tokens": r["N"], "runs": r.get("runs", ""),
            "recompute_ms": r_(f(r["recompute_ms_mean"])), "recompute_ms_std": r_(f(r.get("recompute_ms_std"))),
            "resume_total_ms": r_(f(r["resume_total_ms_mean"])), "speedup": r_(f(r["speedup_mean"])),
            "rss_after_prefill_MiB": r.get("rss_after_prefill_mb_mean", ""),
            "swap_after_restore_MiB_max": r.get("swap_after_restore_mb_max", ""),
            "vmstat_si_KiB": si if vm else "미측정", "vmstat_so_KiB": so if vm else "미측정",
            "all_match": r.get("all_match", ""),
        })
    return out


def ctx_idle(root):
    """D4 idle_* 조건: --ctx별 대화 없을 때 메모리, KV 버퍼, swap (meta.json에서)."""
    out = []
    for meta_path in sorted((root / "D4").glob("*/meta.json")):
        try:
            m = json.loads(meta_path.read_text())
        except Exception:
            continue
        a = m.get("args", {})
        if not a.get("idle_only"):
            continue
        for model, sm in m.get("server_mem", {}).items():
            i0 = m.get("idle_mem", {}).get(model, {})
            i1 = m.get("idle_mem_settled", {}).get(model, {})
            out.append({
                "model": model, "condition": meta_path.parent.name, "ctx": a.get("ctx", ""),
                "mem_limit": a.get("mem_limit") or "없음", "mem_high": a.get("mem_high") or "",
                "n_ctx": sm.get("n_ctx", ""), "kv_buffer_MiB": sm.get("kv_buffer_mib", ""),
                "kv_theory_MiB(계산값)": "", "compute_buffer_MiB": sm.get("compute_buffer_mib", ""),
                "repack_buffer_MiB": sm.get("repack_buffer_mib", ""), "mapped_model_MiB": sm.get("mapped_model_mib", ""),
                "rss_MiB": i1.get("VmRSS", i0.get("VmRSS", "")), "anon_MiB": i1.get("RssAnon", ""),
                "file_MiB": i1.get("RssFile", ""), "swap_MiB": i1.get("VmSwap", ""),
                "cgroup_current_MiB": i1.get("memory.current", ""), "cgroup_swap_MiB": i1.get("memory.swap.current", ""),
                "rss_at_ready_MiB": i0.get("VmRSS", ""), "swap_at_ready_MiB": i0.get("VmSwap", ""),
                "result_dir": str(meta_path.parent),
            })
    return sorted(out, key=lambda x: (x["model"] != "qwen", x["mem_limit"], int(x["ctx"] or 0)))


def model_compare(cond_rows, length_rows):
    out = []
    lr = {(x["stage"], x["condition"], x["model"], x["cache"], x["n_tokens"]): x for x in length_rows}
    cr = {(x["stage"], x["condition"], x["model"]): x for x in cond_rows}
    for (st, cn, cache, N) in sorted({(k[0], k[1], k[3], k[4]) for k in lr}):
        q, l = lr.get((st, cn, "qwen", cache, N)), lr.get((st, cn, "llama", cache, N))
        if not (q and l):
            continue
        cq, cl = cr.get((st, cn, "qwen"), {}), cr.get((st, cn, "llama"), {})

        def ratio(a, b):
            a, b = f(a), f(b)
            return r_(a / b, 2) if a and b else ""
        out.append({
            "stage": st, "condition": cn, "cache": cache, "n_tokens": N,
            "recompute_ms_qwen": q["recompute_ms"], "recompute_ms_llama": l["recompute_ms"],
            "resume_ms_qwen": q["resume_total_ms"], "resume_ms_llama": l["resume_total_ms"],
            "speedup_qwen": q["speedup"], "speedup_llama": l["speedup"],
            "r_qwen": q["r_tok_s"], "r_llama": l["r_tok_s"],
            "Bstar_qwen": q["Bstar_MB_s(계산값)"], "Bstar_llama": l["Bstar_MB_s(계산값)"],
            "T0_qwen": cq.get("T0_ms", ""), "T0_llama": cl.get("T0_ms", ""),
            "Nstar_qwen": cq.get("Nstar_tok(계산값)", ""), "Nstar_llama": cl.get("Nstar_tok(계산값)", ""),
            "rss_inc_qwen": q["rss_increase_MiB"], "rss_inc_llama": l["rss_increase_MiB"],
            # 배율 비(Q/L) = 재계산 비(L/Q, 계산 비용) × 복원 비(L/Q, 로드 비용)의 비
            "recompute_ratio_L/Q": ratio(l["recompute_ms"], q["recompute_ms"]),
            "resume_ratio_L/Q": ratio(l["resume_total_ms"], q["resume_total_ms"]),
            "speedup_ratio_Q/L": ratio(q["speedup"], l["speedup"]),
        })
    return out


def tiers(cond_rows, length_rows, S):
    """기기 등급별: T1(D5 rpi_like 실측), T4(D1 실측), UFS·NVMe(D1의 r, T0 + 해당 B, 계산값)."""
    out = []
    cr = {(x["stage"], x["condition"], x["model"]): x for x in cond_rows}
    lr = {(x["stage"], x["condition"], x["model"], x["cache"], x["n_tokens"]): x for x in length_rows}
    for model in sorted(S, key=lambda m: m != "qwen"):
        s = S[model]["s_bytes_per_token"]
        for tier, key, src in (("T1 저사양 보드 (라즈베리파이 4급 흉내)", ("D5", "rpi_like"), "실측"),
                               ("T4 PC (SATA SSD)", ("D1", "nolimit"), "실측")):
            c = cr.get((*key, model))
            if not c:
                out.append({"tier": tier, "model": model, "kind": "미측정"})
                continue
            out.append({"tier": tier, "model": model, "r_tok_s": c["r_fit_tok_s"], "B_MB_s": c["B_MB_s"],
                        "Bstar_MB_s": c["Bstar_MB_s(계산값)"], "T0_ms": c["T0_ms"],
                        "Nstar_tok": c["Nstar_tok(계산값)"], "Nstar_obs": c["Nstar_tok(실측 교차)"],
                        "speedup_4096": c["speedup_4096"] or "미측정",
                        "kind": f"{src} ({key[0]}/{key[1]}); B*, N*는 계산값", "source": c["result_dir"]})
        base = cr.get(("D1", "nolimit", model))
        rec4096 = f(lr.get(("D1", "nolimit", model, "cold", 4096), {}).get("recompute_ms"))
        for tier, B in DEVICE_TIERS:
            if not base:
                out.append({"tier": tier, "model": model, "B_MB_s": B, "kind": "미측정 (D1 없음)"})
                continue
            r, T0 = f(base["r_fit_tok_s"]), f(base["T0_ms"])
            per_tok = 1000.0 / r - (s / MB) / B * 1000 if r else None
            nstar = T0 / per_tok if (T0 is not None and per_tok and per_tok > 0) else None
            sp = rec4096 / (T0 + 4096 * s / MB / B * 1000) if (rec4096 and T0 is not None) else None
            out.append({"tier": tier, "model": model, "r_tok_s": r_(r), "B_MB_s": B,
                        "Bstar_MB_s": r_(s * r / MB if r else None), "T0_ms": r_(T0),
                        "Nstar_tok": r_(nstar, 1), "Nstar_obs": "-", "speedup_4096": r_(sp),
                        "kind": "계산값 (D1의 r·T0·재계산(4096) + 해당 B)", "source": base["result_dir"]})
    return out


# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(description="2차 실험 분석 (단계 E)")
    p.add_argument("--out-root", default=str(HOME / "aiwork/results/phase2"))
    p.add_argument("--dest", default="", help="결과 폴더 (기본: <out-root>/analysis)")
    a = p.parse_args()
    root = Path(a.out_root).expanduser()
    dest = Path(a.dest).expanduser() if a.dest else root / "analysis"
    dest.mkdir(parents=True, exist_ok=True)

    rows = load(root)
    S = kv_size_per_token(rows)
    cond_rows = per_condition(rows, S)
    length_rows = per_length(rows, S, cond_rows)
    d2 = d2_crossover(rows, S, length_rows)
    d4 = d4_pressure(rows, length_rows)
    mc = model_compare(cond_rows, length_rows)
    tr = tiers(cond_rows, length_rows, S)
    ci = ctx_idle(root)
    for x in ci:                          # 이론 KV 버퍼 = s × ctx
        s_ = S.get(x["model"], {}).get("s_bytes_per_token")
        if s_ and x["n_ctx"]:
            x["kv_theory_MiB(계산값)"] = round(s_ * int(x["n_ctx"]) / MIB, 1)
    mem = [x for x in length_rows if x["rss_increase_MiB"] != "" and not
           next((r.get("mem_limit") for r in rows if r["stage"] == x["stage"] and r["condition"] == x["condition"]), "")]
    save = [x for x in length_rows if x["cache"] == "cold" or x["stage"] == "D2"]

    files = {
        "kv_size_per_token.csv": list(S.values()), "per_condition.csv": cond_rows,
        "per_length.csv": length_rows, "d2_crossover.csv": d2, "d4_pressure.csv": d4,
        "memory_rss.csv": mem, "save_cost.csv": save, "model_compare.csv": mc, "device_tiers.csv": tr,
        "d4_ctx_idle.csv": ci,
    }
    for name, data in files.items():
        write_csv(dest / name, data)

    md = [f"# 2차 실험 분석 결과\n\n생성: {dt.datetime.now():%Y-%m-%d %H:%M} · 입력: `{root / 'sweep_summary.csv'}`\n",
          "단위: 시간 ms, 속도 MB/s(10^6 바이트), 메모리 MiB, s 바이트/토큰, r 토큰/s. "
          "\"계산값\"은 측정값으로 식을 계산한 것, \"실측\"은 측정에서 직접 읽은 것.\n",
          "## 토큰당 KV 크기 s\n", md_table(list(S.values()), ["model", "s_bytes_per_token", "header_bytes", "lengths"]),
          "\n## 조건별 r, T0, B*, N*\n",
          md_table(cond_rows, ["stage", "condition", "model", "cache", "status", "r_fit_tok_s", "B_MB_s", "T0_ms",
                               "Bstar_MB_s(계산값)", "Nstar_tok(계산값)", "Nstar_tok(실측 교차)", "speedup_4096"]),
          "\n## D2 손익분기식 검증 (B* 예측 vs 실측 교차)\n",
          md_table(d2, ["model", "n_tokens", "B_cross_MB_s(실측 보간)", "Bstar_MB_s(계산값)",
                        "Bstar_T0_MB_s(계산값)", "err_Bstar_%", "err_Bstar_T0_%", "speedup_by_B"]),
          "\n## 메모리 (제한 없음): RSS 증가 vs 이론 KV 크기\n",
          md_table(mem, ["stage", "condition", "model", "cache", "n_tokens", "rss_increase_MiB", "kv_theory_MiB(계산값)"]),
          "\n## D4 컨텍스트 크기별 대화 없을 때 메모리 (서버 시작 전 캐시 비움)\n",
          md_table(ci, ["model", "mem_limit", "ctx", "kv_buffer_MiB", "kv_theory_MiB(계산값)", "compute_buffer_MiB",
                        "repack_buffer_MiB", "rss_MiB", "anon_MiB", "file_MiB", "swap_MiB"]),
          "\n## D4 메모리 압박\n",
          md_table(d4, ["model", "mem_limit", "status", "n_tokens", "runs", "recompute_ms", "resume_total_ms", "speedup",
                        "swap_after_restore_MiB_max", "vmstat_si_KiB", "vmstat_so_KiB", "all_match"]),
          "\n## 저장 비용과 본전 재사용 횟수\n",
          md_table(save, ["stage", "condition", "model", "cache", "n_tokens", "save_total_ms", "resume_total_ms",
                          "recompute_ms", "breakeven_reuse"]),
          "\n## 모델 비교 (Qwen vs Llama)\n",
          md_table(mc, ["stage", "condition", "cache", "n_tokens", "r_qwen", "r_llama", "recompute_ratio_L/Q",
                        "resume_ratio_L/Q", "speedup_qwen", "speedup_llama", "speedup_ratio_Q/L"]),
          "\n## 기기 등급별 정리\n",
          md_table(tr, ["tier", "model", "r_tok_s", "B_MB_s", "Bstar_MB_s", "T0_ms", "Nstar_tok", "Nstar_obs",
                        "speedup_4096", "kind"]),
          f"\n출처: `{root}` 아래 각 조건 폴더 (표의 result_dir 열은 `{dest}`의 CSV에 있음)\n"]
    (dest / "analysis.md").write_text("\n".join(md))
    print(f"분석 결과: {dest}")
    for name in files:
        if (dest / name).exists():
            print(f"  {name}")
    print("  analysis.md")


if __name__ == "__main__":
    main()
