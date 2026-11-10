#!/usr/bin/env python3
"""
2차 실험 그래프. <out-root>/sweep_summary.csv 와 analyze_results.py의 계산을 써서
<out-root>/plots/*.png 를 그린다 (한글 축·범례, 로그 축은 축 이름에 "로그" 표시, 모두 Qwen·Llama 함께).

  fig1_recompute_vs_store_load.png  토큰별 다시 계산 vs 저장·로드 (PC 실측 + Galaxy S25 예측)
  fig2_load_by_storage.png          저장장치 속도별 토큰별 로드 시간 (+ UFS 4.0 예측)
  fig3_prefill_by_cpu.png           CPU 조건별 Prefill 시간 (+ Galaxy S25 NPU 예측)
  fig4_breakeven_read_speed.png     읽기 속도 vs 배율, B* 예측선 (손익분기)
  fig5_memory_ctx.png               컨텍스트 크기별 대화 없을 때 메모리
  fig6_memory_pressure.png          메모리 상한별 재계산·복원 시간
  fig7_memory_tokens.png            토큰 수별 메모리 증가 vs 이론 KV 크기
  fig8_model_compare.png            같은 조건에서 Qwen vs Llama
  fig9_device_criteria.png          기기별 경계 토큰 수 N*와 4,096토큰 배율

예시: ~/aiwork/venv/bin/python scripts/plot_results.py --out-root ~/aiwork/results/phase2
"""

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter  # noqa: E402

from matplotlib import font_manager  # noqa: E402


def use_korean_font():
    """koreanize-matplotlib 패키지에 들어 있는 NanumGothic을 직접 등록한다.
    (이 패키지는 Python 3.12+에서 distutils가 없어 import가 실패하므로 폰트 파일만 쓴다)"""
    import importlib.util
    spec = importlib.util.find_spec("koreanize_matplotlib")
    fonts = sorted(Path(spec.submodule_search_locations[0], "fonts").glob("NanumGothic*.ttf")) if spec else []
    for ttf in fonts:
        font_manager.fontManager.addfont(str(ttf))
    if fonts:
        plt.rcParams["font.family"] = "NanumGothic"
        return True
    names = {x.name for x in font_manager.fontManager.ttflist}
    for name in ("NanumGothic", "Noto Sans CJK KR", "Noto Sans KR", "UnDotum"):
        if name in names:
            plt.rcParams["font.family"] = name
            return True
    print("경고: 한글 폰트 없음 → 한글이 깨질 수 있음 (pip install -r requirements.txt)")
    return False

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_results as an  # noqa: E402

HOME = Path.home()
REPO_ROOT = Path(__file__).resolve().parent.parent

# 범주색: 고정 순서 (참조 팔레트 1~5번). 모델은 항상 Qwen=1번, Llama=2번
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
MODEL_COLOR = {"qwen": CAT[0], "llama": CAT[1]}
MODEL_NAME = {"qwen": "Qwen 0.5B", "llama": "Llama 1B"}
MARKERS = ["o", "s", "^", "D", "v", "P", "X", "*"]
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 2, "lines.markersize": 6,
    "legend.frameon": False, "axes.unicode_minus": False, "font.size": 10, "axes.titlesize": 11,
    "figure.dpi": 110,
})
use_korean_font()
NUM = FuncFormatter(lambda v, _: f"{v:,.0f}" if v >= 1 else f"{v:g}")


def f(x):
    return an.f(x)


def models_in(rows):
    return [m for m in ("qwen", "llama") if any(r["model"] == m for r in rows)]


def save(fig, out, name, made):
    fig.tight_layout()
    path = out / name
    fig.savefig(path, dpi=150)
    plt.close(fig)
    made.append(path)


def logx(ax, label):
    ax.set_xscale("log", base=2)
    ax.xaxis.set_major_formatter(NUM)
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel(label)


# ---------------------------------------------------------------- 그래프

def plot_d2(rows, length_rows, out, made):
    d2 = [r for r in rows if r["stage"] == "D2" and r["storage"] == "raw"]
    if not d2:
        return
    ms = models_in(d2)
    fig, axes = plt.subplots(1, len(ms), figsize=(6.2 * len(ms), 4.8), sharey=True, sharex=True, squeeze=False)
    pred = {(x["model"], x["n_tokens"]): f(x["Bstar_MB_s(계산값)"]) for x in length_rows
            if x["stage"] == "D2" and x["condition"] == "nolimit"}
    lengths = sorted({r["N"] for r in d2})
    for ax, m in zip(axes[0], ms):
        for i, N in enumerate(lengths):
            c, mk = CAT[i % len(CAT)], MARKERS[i % len(MARKERS)]
            pts = sorted((f(r["disk_read_mb_per_s"]), f(r["speedup_mean"]), r["kv_fs"] == "tmpfs")
                         for r in d2 if r["model"] == m and r["N"] == N and f(r["disk_read_mb_per_s"]))
            ssd = [(b, s) for b, s, ram in pts if not ram]
            ram = [(b, s) for b, s, r_ in pts if r_]
            if ssd:
                ax.plot([b for b, _ in ssd], [s for _, s in ssd], color=c, marker=mk, label=f"{N:,}토큰")
            if ram:
                ax.scatter([b for b, _ in ram], [s for _, s in ram], color=c, marker=mk, s=60,
                           facecolors="none", linewidths=1.8)
            if pred.get((m, N)):
                ax.axvline(pred[(m, N)], color=c, ls=":", lw=1.2)
        ax.axhline(1, color=INK, lw=1.2)
        ax.text(0.02, 1.0, " 배율 1 (손익분기)", color=INK, fontsize=8,
                va="bottom", transform=ax.get_yaxis_transform())
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.xaxis.set_major_formatter(NUM)
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.yaxis.set_major_formatter(NUM)
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.yaxis.set_major_locator(LogLocator(10, subs=(1, 2, 5)))
        ax.set_xlabel("저장장치 읽기 속도 (MB/s, 실측, 로그)")
        ax.set_title(f"{MODEL_NAME[m]}: 읽기 속도 vs 배율\n(점선 세로선 = 길이별 B* = s×r 예측, 빈 원 = RAM 디스크 warm)")
        ax.legend(fontsize=8, title="길이")
    axes[0][0].set_ylabel("배율 = 재계산 ÷ 복원 (로그)")
    save(fig, out, "fig4_breakeven_read_speed.png", made)


def plot_d3(cond_rows, out, made):
    d3 = [c for c in cond_rows if c["stage"] == "D3"]
    if not d3:
        return
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.5), squeeze=False)
    for col, (key, xl, sel) in enumerate((
            ("threads", "스레드·코어 수 (클럭 3600MHz)", lambda c: str(c["max_freq"]) == "3600"),
            ("max_freq", "최대 클럭 (MHz, 스레드·코어 8)", lambda c: str(c["threads"]) == "8"))):
        for row, (yk, yl) in enumerate((("r_fit_tok_s", "Prefill 처리 속도 r (토큰/s)"),
                                         ("Bstar_MB_s(계산값)", "B* = s×r (MB/s, 계산값)"))):
            ax = axes[row][col]
            for m in ("qwen", "llama"):
                pts = sorted((f(c[key]), f(c[yk])) for c in d3 if c["model"] == m and sel(c) and f(c[key]))
                if pts:
                    ax.plot([a for a, _ in pts], [b for _, b in pts], color=MODEL_COLOR[m],
                            marker="o" if m == "qwen" else "s", label=MODEL_NAME[m])
                    for a, b in pts[-1:]:
                        ax.annotate(f"{b:,.0f}" if b >= 10 else f"{b:.1f}", (a, b), textcoords="offset points",
                                    xytext=(4, 4), fontsize=8, color=INK2)
            ax.set_xlabel(xl)
            ax.set_ylabel(yl)
            ax.set_ylim(bottom=0)
            ax.legend(fontsize=8)
    axes[0][0].set_title("스레드 수에 따른 r")
    axes[0][1].set_title("클럭에 따른 r")
    axes[1][0].set_title("스레드 수에 따른 B*")
    axes[1][1].set_title("클럭에 따른 B*")
    save(fig, out, "d3_cpu.png", made)


def plot_d4(rows, length_rows, out, made):
    mem = [x for x in length_rows if x["rss_increase_MiB"] != "" and x["cache"] == "cold" and not
           next((r.get("mem_limit") for r in rows if r["stage"] == x["stage"] and r["condition"] == x["condition"]), "")]
    if mem:
        fig, ax = plt.subplots(figsize=(7.5, 4.8))
        for m in ("qwen", "llama"):
            pts = {}
            for x in mem:
                if x["model"] == m:
                    pts.setdefault(x["n_tokens"], (f(x["rss_increase_MiB"]), f(x["kv_theory_MiB(계산값)"])))
            if not pts:
                continue
            ns = sorted(pts)
            ax.plot(ns, [pts[n][0] for n in ns], color=MODEL_COLOR[m], marker="o", label=f"{MODEL_NAME[m]} 실측 RSS 증가")
            ax.plot(ns, [pts[n][1] for n in ns], color=MODEL_COLOR[m], ls="--", lw=1.4,
                    label=f"{MODEL_NAME[m]} 이론 KV 크기 (s×토큰, 계산값)")
        logx(ax, "프롬프트 길이 (토큰, 로그)")
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(NUM)
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.yaxis.set_major_locator(LogLocator(10, subs=(1, 2, 5)))
        ax.set_ylabel("메모리 증가량 (MiB, 로그)")
        ax.set_title("토큰 수별 메모리 증가: RSS(재계산 직후) - 대화 없음 RSS")
        ax.legend(fontsize=8)
        save(fig, out, "fig7_memory_tokens.png", made)

    d4 = [r for r in rows if r["stage"] == "D4" and r["storage"] == "raw" and r.get("mem_limit")]
    if not d4:
        return
    order = sorted({r["mem_limit"] for r in d4}, key=lambda v: -an.f(v[:-1]) * (1024 if v[-1] == "G" else 1))
    lengths = sorted({r["N"] for r in d4})
    ms = models_in(d4)
    fig, axes = plt.subplots(1, len(ms), figsize=(6.2 * len(ms), 4.6), sharey=True, squeeze=False)
    status = {(r["condition"]): r.get("status", "") for r in d4}
    for ax, m in zip(axes[0], ms):
        xs = range(len(order))
        for i, N in enumerate(lengths):
            c, mk = CAT[(i + 2) % len(CAT)], MARKERS[i % len(MARKERS)]
            def get(key):
                d = {r["mem_limit"]: f(r[key]) for r in d4 if r["model"] == m and r["N"] == N}
                return [d.get(o) for o in order]
            ax.plot(xs, get("recompute_ms_mean"), color=c, marker=mk, label=f"재계산 {N:,}토큰")
            ax.plot(xs, get("resume_total_ms_mean"), color=c, marker=mk, ls="--", label=f"복원 {N:,}토큰")
        labels = []
        for o in order:
            cond = next((r["condition"] for r in d4 if r["mem_limit"] == o), "")
            st = status.get(cond, "")
            labels.append(o + ("\n(서버 종료)" if st == "server_died" else ""))
        ax.set_xticks(list(xs), labels)
        ax.set_xlabel("메모리 상한 (MemoryMax, 완만한 상한 = 75%, swap 1G)")
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(NUM)
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.yaxis.set_major_locator(LogLocator(10, subs=(1, 2, 5)))
        ax.set_title(f"{MODEL_NAME[m]}: 메모리 상한별 재계산·복원 시간 (cold)")
        ax.legend(fontsize=7, ncol=2)
    axes[0][0].set_ylabel("시간 (ms, 로그)")
    save(fig, out, "fig6_memory_pressure.png", made)


def plot_ctx_idle(ci, out, made):
    if not ci:
        return
    ms = [m for m in ("qwen", "llama") if any(x["model"] == m for x in ci)]
    fig, axes = plt.subplots(1, len(ms), figsize=(6.2 * len(ms), 4.6), sharey=True, squeeze=False)
    for ax, m in zip(axes[0], ms):
        for lim, ls in (("없음", "-"), ("1536M", "--")):
            pts = sorted((int(x["ctx"]), x) for x in ci if x["model"] == m and x["mem_limit"] == lim)
            if not pts:
                continue
            xs = [a for a, _ in pts]
            tag = "제한 없음" if lim == "없음" else "상한 1.5G"
            for i, (key, name) in enumerate((("anon_MiB", "익명 메모리(RssAnon)"), ("kv_buffer_MiB", "KV 버퍼(로그)"),
                                             ("swap_MiB", "swap(VmSwap)"))):
                ys = [f(x[key]) for _, x in pts]
                if lim == "없음" and key == "swap_MiB":
                    continue
                if lim != "없음" and key == "kv_buffer_MiB":
                    continue
                ax.plot(xs, [y if y else None for y in ys], color=CAT[[0, 3, 7][i]], ls=ls,
                        marker=MARKERS[i], label=f"{name}, {tag}")
        logx(ax, "컨텍스트 크기 --ctx (토큰, 로그)")
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(NUM)
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.yaxis.set_major_locator(LogLocator(10, subs=(1, 2, 5)))
        ax.set_title(f"{MODEL_NAME[m]}: 컨텍스트 크기별 대화 없을 때 메모리")
        ax.legend(fontsize=7.5)
    axes[0][0].set_ylabel("메모리 (MiB, 로그)")
    save(fig, out, "fig5_memory_ctx.png", made)


def plot_model_compare(length_rows, out, made):
    pairs = [("D1", "nolimit", "제한 없음 (D1)"), ("D5", "rpi_like", "라즈베리파이 흉내 (D5b)")]
    pairs = [p for p in pairs if any(x["stage"] == p[0] and x["condition"] == p[1] for x in length_rows)]
    if not pairs:
        return
    fig, axes = plt.subplots(len(pairs), 3, figsize=(15, 4.2 * len(pairs)), squeeze=False)
    for row, (st, cn, title) in enumerate(pairs):
        for col, (key, yl) in enumerate((("recompute_ms", "재계산 시간 (ms, 로그)"),
                                          ("resume_total_ms", "복원 시간 cold (ms, 로그)"),
                                          ("speedup", "배율 = 재계산 ÷ 복원 (로그)"))):
            ax = axes[row][col]
            for m in ("qwen", "llama"):
                pts = sorted((x["n_tokens"], f(x[key])) for x in length_rows
                             if x["stage"] == st and x["condition"] == cn and x["model"] == m
                             and x["cache"] == "cold" and f(x[key]))
                if pts:
                    ax.plot([a for a, _ in pts], [b for _, b in pts], color=MODEL_COLOR[m],
                            marker="o" if m == "qwen" else "s", label=MODEL_NAME[m])
            if key == "speedup":
                ax.axhline(1, color=INK, lw=1)
            logx(ax, "프롬프트 길이 (토큰, 로그)")
            ax.set_yscale("log")
            ax.yaxis.set_major_formatter(NUM)
            ax.yaxis.set_minor_formatter(NullFormatter())
            ax.yaxis.set_major_locator(LogLocator(10, subs=(1, 2, 5)))
            ax.set_ylabel(yl)
            ax.set_title(f"{title}: {yl.split(' (')[0]}")
            ax.legend(fontsize=8)
    save(fig, out, "fig8_model_compare.png", made)


def series(rows, stage, cond, model, key, cache="cold"):
    pts = sorted((r["N"], f(r[key])) for r in rows if r["stage"] == stage and r["condition"] == cond
                 and r["model"] == model and r["storage"] == "raw" and r["cache"] == cache and f(r[key]) is not None)
    return [a for a, _ in pts], [b for _, b in pts]


def log_axes(ax, xlabel="프롬프트 길이 (토큰, 로그)", ylabel="시간 (ms, 로그)"):
    logx(ax, xlabel)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(NUM)
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_major_locator(LogLocator(10, subs=(1, 2, 5)))
    ax.set_ylabel(ylabel)


S25_NS = [16, 32, 64, 128, 256, 512, 1024, 2048, 4096]


def s25_band(ax, color, label):
    """Galaxy S25 Prefill 예측 범위 (w4a16 ~ w4, 128토큰 단위 처리)."""
    lo = [an.s25_prefill_ms(n, "w4a16") for n in S25_NS]
    hi = [an.s25_prefill_ms(n, "w4") for n in S25_NS]
    ax.fill_between(S25_NS, lo, hi, color=color, alpha=0.18, lw=0, step=None)
    ax.plot(S25_NS, lo, color=color, ls="--", lw=1.4)
    ax.plot(S25_NS, hi, color=color, ls="--", lw=1.4, label=label)


def plot_fig1(rows, S, cond_rows, out, made):
    """토큰별 다시 계산 vs 저장·로드: 공용 PC 실측(D1) + Galaxy S25 예측(Llama)."""
    if not any(r["stage"] == "D1" for r in rows):
        return
    T0 = {c["model"]: f(c["T0_ms"]) for c in cond_rows if c["stage"] == "D1" and c["condition"] == "nolimit"}
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), sharey=True)
    for ax, m in zip(axes, ("qwen", "llama")):
        ax.plot(*series(rows, "D1", "nolimit", m, "recompute_ms_mean"), color=CAT[0], marker="o",
                label="다시 계산 (PC 실측)")
        ax.plot(*series(rows, "D1", "nolimit", m, "resume_total_ms_mean"), color=CAT[2], marker="s",
                label="로드 cold (PC 실측)")
        ax.plot(*series(rows, "D1", "nolimit", m, "save_total_ms_mean"), color=CAT[3], marker="^",
                label="저장 (PC 실측, fsync 포함)")
        if m == "llama" and m in S:
            s, h = S[m]["s_bytes_per_token"], S[m]["header_bytes"]
            s25_band(ax, CAT[0], "다시 계산 (Galaxy S25 NPU 예측, w4a16~w4)")
            ax.plot(S25_NS, [an.s25_load_ms(n, s, h, T0.get(m) or 0) for n in S25_NS], color=CAT[2], ls="--",
                    lw=1.4, label="로드 (S25 예측: PC 실측 T0 + 파일÷4,200MB/s)")
            ax.plot(S25_NS, [an.s25_save_ms(n, s, h) for n in S25_NS], color=CAT[3], ls="--", lw=1.4,
                    label="저장 (S25 예측: 파일÷2,800MB/s)")
        else:
            ax.text(0.03, 0.97, "Galaxy S25 예측: Qwen 공개 자료 없음", transform=ax.transAxes, va="top",
                    fontsize=8.5, color=INK2)
        log_axes(ax)
        ax.set_title(f"{MODEL_NAME[m]}: 다시 계산 vs 저장·로드 (실선 실측, 점선 예측)")
        ax.legend(fontsize=7.5, loc="lower right")
    save(fig, out, "fig1_recompute_vs_store_load.png", made)


def plot_fig2(rows, S, cond_rows, out, made):
    """저장장치 속도별 토큰별 로드 시간 (D2) + UFS 4.0 예측."""
    d2 = [r for r in rows if r["stage"] == "D2"]
    if not d2:
        return
    T0 = {c["model"]: f(c["T0_ms"]) for c in cond_rows if c["stage"] == "D2" and c["condition"] == "nolimit"}
    conds = [("read5M", "cold", "5MB/s"), ("read10M", "cold", "10MB/s"), ("read20M", "cold", "20MB/s"),
             ("read44M", "cold", "44MB/s (microSD 수준)"), ("read100M", "cold", "100MB/s"),
             ("nolimit", "cold", "제한 없음 (SATA, 약 540MB/s)"), ("ramdisk", "warm", "RAM 디스크")]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), sharey=True)
    for ax, m in zip(axes, ("qwen", "llama")):
        for i, (c, cache, lab) in enumerate(conds):
            xs, ys = series(rows, "D2", c, m, "resume_total_ms_mean", cache)
            if xs:
                ax.plot(xs, ys, color=CAT[i], marker=MARKERS[i], label=f"로드 {lab}")
        if m in S:
            s, h = S[m]["s_bytes_per_token"], S[m]["header_bytes"]
            ns = [16, 64, 256, 1024, 4096]
            ax.plot(ns, [an.s25_load_ms(n, s, h, T0.get(m) or 0) for n in ns], color=CAT[7], ls="--",
                    marker=MARKERS[7], label="로드 UFS 4.0 4,200MB/s (예측)")
        xs, ys = series(rows, "D2", "nolimit", m, "recompute_ms_mean")
        ax.plot(xs, ys, color=INK, lw=2.6, label="다시 계산 (참고, 같은 CPU)")
        log_axes(ax)
        ax.set_title(f"{MODEL_NAME[m]}: 저장장치 속도별 로드 시간")
        ax.legend(fontsize=7.2, loc="upper left", ncol=2)
    save(fig, out, "fig2_load_by_storage.png", made)


def plot_fig3(rows, out, made):
    """CPU 조건별 토큰별 Prefill(다시 계산) 시간 (D3, D5) + Galaxy S25 NPU 예측."""
    conds = [("D3", "t2_f3600", "2스레드 3.6GHz"), ("D3", "t4_f3600", "4스레드 3.6GHz"),
             ("D3", "t8_f3600", "8스레드 3.6GHz (PC 기준)"), ("D3", "t8_f2400", "8스레드 2.4GHz"),
             ("D3", "t8_f1500", "8스레드 1.5GHz"), ("D5", "rpi_like", "라즈베리파이 흉내 (4코어 1.5GHz)"),
             ("D5", "phase1_repro", "1차 조건 (4코어 2.4GHz, 사용률 300%)")]
    if not any(r["stage"] in ("D3", "D5") for r in rows):
        return
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), sharey=True)
    for ax, m in zip(axes, ("qwen", "llama")):
        for i, (st, c, lab) in enumerate(conds):
            xs, ys = series(rows, st, c, m, "recompute_ms_mean")
            if xs:
                ax.plot(xs, ys, color=CAT[i], marker=MARKERS[i], label=lab,
                        ls=":" if c == "phase1_repro" else "-")
        if m == "llama":
            s25_band(ax, CAT[7], "Galaxy S25 NPU (예측, w4a16~w4)")
        else:
            ax.text(0.03, 0.97, "Galaxy S25 예측: Qwen 공개 자료 없음", transform=ax.transAxes, va="top",
                    fontsize=8.5, color=INK2)
        log_axes(ax, ylabel="Prefill(다시 계산) 시간 (ms, 로그)")
        ax.set_title(f"{MODEL_NAME[m]}: CPU 조건별 Prefill 시간")
        ax.legend(fontsize=7.2, loc="upper left")
    save(fig, out, "fig3_prefill_by_cpu.png", made)


def plot_fig9(dev_rows, out, made):
    """기기별 판단 기준: 경계 토큰 수 N*와 4,096토큰 배율."""
    rows = [d for d in dev_rows if f(d.get("Nstar_tok")) is not None]
    if not rows:
        return
    labels = []
    for d in rows:
        dev = d["device"].split(" (")[0]
        k = d["kind"]
        labels.append(f"{dev}\n{MODEL_NAME[d['model']]}\n{k}")
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    for ax, key, yl, title in ((axes[0], "Nstar_tok", "경계 토큰 수 N* (토큰, 계산값)",
                                "N* = T0 ÷ (1/r - s/B): 이보다 길면 저장·로드가 이득"),
                               (axes[1], "speedup_4096", "4,096토큰 배율 (다시 계산 ÷ 로드)",
                                "4,096토큰에서 저장·로드가 몇 배 빠른가")):
        vals = [f(d[key]) or 0 for d in rows]
        cols = [MODEL_COLOR[d["model"]] for d in rows]
        bars = ax.bar(range(len(rows)), vals, color=cols, width=0.62)
        for b, d, v in zip(bars, rows, vals):
            if d["kind"].startswith("예측"):
                b.set_hatch("//")
                b.set_edgecolor(SURF)
            ax.annotate(f"{v:,.1f}", (b.get_x() + b.get_width() / 2, v), textcoords="offset points",
                        xytext=(0, 3), ha="center", fontsize=8, color=INK2)
        ax.set_xticks(range(len(rows)), labels, fontsize=7.2)
        ax.set_ylabel(yl)
        ax.set_title(title)
        ax.margins(y=0.15)
    from matplotlib.patches import Patch
    axes[0].legend(handles=[Patch(color=MODEL_COLOR["qwen"], label="Qwen 0.5B"),
                            Patch(color=MODEL_COLOR["llama"], label="Llama 1B"),
                            Patch(facecolor=INK2, hatch="//", edgecolor=SURF, label="빗금 = 예측 (실측 아님)")],
                   fontsize=8, loc="upper left")
    save(fig, out, "fig9_device_criteria.png", made)


def main():
    p = argparse.ArgumentParser(description="2차 실험 그래프")
    p.add_argument("--out-root", default=str(HOME / "aiwork/results/phase2"))
    p.add_argument("--dest", default="", help="그래프 폴더 (기본: <out-root>/plots)")
    a = p.parse_args()
    root = Path(a.out_root).expanduser()
    out = Path(a.dest).expanduser() if a.dest else root / "plots"
    out.mkdir(parents=True, exist_ok=True)

    rows = an.load(root)
    S = an.kv_size_per_token(rows)
    cond_rows = an.per_condition(rows, S)
    length_rows = an.per_length(rows, S, cond_rows)

    made = []
    dev_rows = an.device_criteria(cond_rows, length_rows, S)
    plot_fig1(rows, S, cond_rows, out, made)
    plot_fig2(rows, S, cond_rows, out, made)
    plot_fig3(rows, out, made)
    plot_d2(rows, length_rows, out, made)          # fig4 손익분기
    plot_ctx_idle(an.ctx_idle(root), out, made)    # fig5 컨텍스트별 메모리
    plot_d4(rows, length_rows, out, made)          # fig6 메모리 압박, fig7 토큰별 메모리
    plot_model_compare(length_rows, out, made)     # fig8 모델 비교
    plot_fig9(dev_rows, out, made)                 # fig9 기기별 판단 기준
    print(f"그래프 {len(made)}개: {out}")
    for pth in made:
        print(f"  {pth.name}")


if __name__ == "__main__":
    main()
