#!/usr/bin/env python3
"""
2차 실험 그래프. <out-root>/sweep_summary.csv 와 analyze_results.py의 계산을 써서
<out-root>/plots/*.png 를 그린다 (한글 축·범례, 로그 축은 축 이름에 "로그" 표시).

  d1_times.png            D1 길이별 재계산 vs 복원(cold·warm), 모델별, 1차 결과 겹침
  d2_speedup_vs_read.png  D2 읽기 속도 vs 배율, 길이별 선, y=1 기준선과 B* 예측선
  d3_cpu.png              D3 스레드·클럭별 Prefill 처리 속도 r과 B*
  d4_memory_rss.png       토큰 수 vs 메모리 증가 (실측 RSS 증가 vs 이론 KV 크기)
  d4_memory_pressure.png  메모리 상한별 재계산·복원 시간
  tiers_nstar.png         기기 등급별 경계 토큰 수 N* 막대 (모델별)
  model_compare.png       같은 조건에서 Qwen vs Llama 재계산·복원·배율

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

def plot_d1(rows, out, made):
    d1 = [r for r in rows if r["stage"] == "D1" and r["storage"] == "raw"]
    if not d1:
        return
    p1 = []
    p1_path = REPO_ROOT / "docs/results/phase1_summary.csv"
    if p1_path.exists():
        p1 = [dict(r, N=int(r["n_tokens"])) for r in csv.DictReader(open(p1_path)) if r["storage"] == "raw"]
    ms = models_in(d1)
    fig, axes = plt.subplots(1, len(ms), figsize=(6 * len(ms), 4.6), sharey=True, squeeze=False)
    for ax, m in zip(axes[0], ms):
        def series(src, key, cache=None):
            pts = sorted((r["N"], f(r[key])) for r in src if r["model"] == m and (cache is None or r["cache"] == cache))
            pts = list(dict(pts).items())            # 같은 길이 중복 제거 (조건이 둘이어도 하나만)
            return [a for a, _ in pts], [b for _, b in pts]
        c = MODEL_COLOR[m]
        ax.plot(*series(d1, "recompute_ms_mean", "cold"), color=c, marker="o", label="재계산 (2차, 제한 없음)")
        ax.plot(*series(d1, "resume_total_ms_mean", "cold"), color=c, marker="s", ls="--", label="복원 cold (2차)")
        ax.plot(*series(d1, "resume_total_ms_mean", "warm"), color=c, marker="^", ls=":", label="복원 warm (2차)")
        if p1:
            ax.plot(*series(p1, "recompute_ms_mean", "cold"), color=INK2, marker="o", lw=1.2, alpha=.8,
                    label="재계산 (1차, 저사양 조건)")
            ax.plot(*series(p1, "resume_total_ms_mean", "cold"), color=INK2, marker="s", ls="--", lw=1.2,
                    alpha=.8, label="복원 cold (1차)")
        logx(ax, "프롬프트 길이 (토큰, 로그)")
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(NUM)
        ax.yaxis.set_minor_formatter(NullFormatter())
        ax.yaxis.set_major_locator(LogLocator(10, subs=(1, 2, 5)))
        ax.set_title(f"{MODEL_NAME[m]}: 길이별 재계산 vs 복원")
        ax.legend(fontsize=8)
    axes[0][0].set_ylabel("시간 (ms, 로그)")
    save(fig, out, "d1_times.png", made)


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
    save(fig, out, "d2_speedup_vs_read.png", made)


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
        save(fig, out, "d4_memory_rss.png", made)

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
    save(fig, out, "d4_memory_pressure.png", made)


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
    save(fig, out, "d4_ctx_idle.png", made)


def plot_tiers(tier_rows, out, made):
    if not tier_rows:
        return
    tiers = sorted(dict.fromkeys(t["tier"] for t in tier_rows))
    fig, ax = plt.subplots(figsize=(10, 4.8))
    w = 0.38
    for j, m in enumerate(("qwen", "llama")):
        vals, kinds = [], []
        for t in tiers:
            row = next((x for x in tier_rows if x["tier"] == t and x["model"] == m), {})
            vals.append(f(row.get("Nstar_tok")) or 0)
            kinds.append(row.get("kind", ""))
        xs = [i + (j - 0.5) * w for i in range(len(tiers))]
        bars = ax.bar(xs, vals, width=w - 0.04, color=MODEL_COLOR[m], label=MODEL_NAME[m])
        for b, v, k in zip(bars, vals, kinds):
            tag = "계산값" if k.startswith("계산값") else ("실측 조건" if k.startswith("실측") else "미측정")
            ax.annotate(f"{v:.1f}\n{tag}" if v else "미측정", (b.get_x() + b.get_width() / 2, b.get_height()),
                        textcoords="offset points", xytext=(0, 3), ha="center", fontsize=7.5, color=INK2)
    ax.set_xticks(range(len(tiers)), [t.replace(" (", "\n(") for t in tiers], fontsize=8.5)
    ax.set_ylabel("경계 토큰 수 N* (토큰, 이보다 길면 저장·로드가 이득)")
    ax.set_title("기기 등급별 \"버리기 vs 저장\" 경계 토큰 수 N* = T0 ÷ (1/r - s/B)")
    ax.margins(y=0.25)
    ax.legend(fontsize=9)
    save(fig, out, "tiers_nstar.png", made)


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
    save(fig, out, "model_compare.png", made)


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
    tier_rows = an.tiers(cond_rows, length_rows, S)

    made = []
    plot_d1(rows, out, made)
    plot_d2(rows, length_rows, out, made)
    plot_d3(cond_rows, out, made)
    plot_d4(rows, length_rows, out, made)
    plot_ctx_idle(an.ctx_idle(root), out, made)
    plot_tiers(tier_rows, out, made)
    plot_model_compare(length_rows, out, made)
    print(f"그래프 {len(made)}개: {out}")
    for pth in made:
        print(f"  {pth.name}")


if __name__ == "__main__":
    main()
