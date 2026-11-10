#!/usr/bin/env python3
"""
조건 목록(configs/phase2/D*.json)을 받아 run_bench.py를 조건마다 차례로 실행한다.

- 결과: <out-root>/<단계>/<조건이름>/ (run_bench.py 결과 + run.log)
- 조건을 시작하기 전마다 다른 실험(Actions 작업, llama-server, 8080 포트)이 있는지 확인하고,
  있으면 그 자리에서 멈춘다 (공용 PC 규칙).
- 조건 하나가 실패하면(서버 종료 등) 기록하고 다음 조건으로 넘어간다.
  출력 불일치·제한 미적용·정리 실패 같은 이상 징후는 멈춘다 (--keep-going으로 무시 가능).
- 끝나면 단계별 summary.csv를 <out-root>/<단계>/sweep_summary.csv로 합친다 (조건 열 포함).

예시:
  ~/aiwork/venv/bin/python scripts/run_sweep.py configs/phase2/D1.json
  ~/aiwork/venv/bin/python scripts/run_sweep.py configs/phase2/D2.json --only read44M,nolimit \\
      --lengths 16,1024 --repeats 1 --out-root ~/aiwork/results/phase2/pilot
  ~/aiwork/venv/bin/python scripts/run_sweep.py configs/phase2/D*.json --merge-only
"""

import argparse
import csv
import datetime as dt
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
REPO_ROOT = Path(__file__).resolve().parent.parent
BENCH = REPO_ROOT / "scripts/run_bench.py"
HELPERS = ["/usr/local/sbin/kvb-io-limit", "/usr/local/sbin/kvb-cpufreq"]
KV_DIRS = [Path("/mnt/ssd/kvcache"), Path("/dev/shm/kvcache")]
CPU = Path("/sys/devices/system/cpu/cpu0/cpufreq")

# sweep_summary.csv 에 summary.csv 앞에 붙이는 조건 열
COND_FIELDS = [
    "stage", "condition", "group", "status",
    "threads", "cores", "max_freq", "cpu_quota", "mem_limit", "mem_high", "swap_max",
    "io_read", "io_write", "kv_dir", "kv_fs",
    "disk_write_mb_per_s", "disk_read_mb_per_s", "disk_read_cache",
    "idle_rss_mb", "warm_idle_rss_mb", "ctx", "bench_repo_commit", "llama_cpp_commit", "result_dir",
]


def log(msg):
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def read(path):
    try:
        return Path(path).read_text().strip()
    except Exception:
        return ""


# ---------------------------------------------------------------- 공용 PC 점검

def busy_reasons(port=8080):
    """다른 실험이 돌고 있으면 이유 목록."""
    why = []
    worker = sh(["pgrep", "-af", "Runner.Worker"])
    if worker:
        why.append(f"GitHub Actions 작업 실행 중 (kv-bench 가능성): {worker.splitlines()[0][:120]}")
    llama = sh(["pgrep", "-a", "llama"])
    if llama:
        why.append(f"llama 프로세스 실행 중: {llama.splitlines()[0][:120]}")
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", port)) == 0:
            why.append(f"{port} 포트 사용 중")
    return why


def leftovers():
    """조건이 끝난 뒤 남으면 안 되는 것들."""
    bad = []
    for d in KV_DIRS:
        if d.exists():
            files = [p for p in d.rglob("*") if p.is_file()]
            if files:
                bad.append(f"KV 파일 남음: {d} ({len(files)}개, 예: {files[0].name})")
    if sh(["pgrep", "-a", "llama-server"]):
        bad.append("llama-server 남음")
    if read(CPU / "scaling_max_freq") != read(CPU / "cpuinfo_max_freq"):
        bad.append(f"CPU 최대 클럭 제한 남음 ({read(CPU / 'scaling_max_freq')} kHz)")
    for sl in ("user.slice", "system.slice"):
        io = sh(["systemctl", "show", sl, "-p", "IOReadBandwidthMax", "-p", "IOWriteBandwidthMax"])
        if any(line.split("=", 1)[1] for line in io.splitlines() if "=" in line):
            bad.append(f"io 제한 남음 ({sl}: {io.replace(chr(10), ' ')})")
    return bad


def reset_limits():
    for cmd in HELPERS:
        if Path(cmd).exists():
            subprocess.run(["sudo", "-n", cmd, "reset"], capture_output=True)


def repo_dirty():
    return sh(["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--untracked-files=no",
               "--", "scripts", "configs"])


# ---------------------------------------------------------------- 실행

def to_cli(args):
    out = []
    for k, v in args.items():
        flag = "--" + k.replace("_", "-")
        if v is True:
            out.append(flag)
        elif v is False or v is None or v == "":
            continue
        else:
            out += [flag, str(v)]
    return out


def load_config(path):
    cfg = json.loads(Path(path).read_text())
    cfg["_path"] = str(path)
    return cfg


def condition_args(cfg, cond, ov):
    a = dict(cfg.get("common", {}))
    a.update(cond.get("args", {}))
    if ov.lengths:
        a["lengths"] = ov.lengths
    if ov.repeats:
        a["repeats"] = ov.repeats
    if ov.model:
        a["model"] = ov.model
    return a


def run_condition(cfg, cond, ov, status_rows):
    stage, name = cfg["stage"], cond["name"]
    out_dir = Path(ov.out_root).expanduser() / stage / name
    a = condition_args(cfg, cond, ov)
    a["out"] = str(out_dir)
    cmd = [ov.python, str(BENCH)] + to_cli(a)
    row = {"stage": stage, "condition": name, "result_dir": str(out_dir),
           "cmd": " ".join(cmd[1:]), "started_at": dt.datetime.now().isoformat(timespec="seconds")}
    if ov.dry_run:
        log(f"(dry-run) {stage}/{name}: {' '.join(cmd[2:])}")
        return "dry-run"

    if out_dir.exists() and (out_dir / "results.csv").exists() and not ov.overwrite:
        log(f"{stage}/{name}: 이미 결과가 있어 건너뜀 ({out_dir}). 다시 하려면 --overwrite")
        return "skipped"
    out_dir.mkdir(parents=True, exist_ok=True)
    log(f"=== {stage}/{name} 시작: {' '.join(cmd[2:])}")
    t0 = time.time()
    with open(out_dir / "run.log", "w") as lf:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             cwd=REPO_ROOT)
        for line in p.stdout:
            lf.write(line)
            lf.flush()
            if not ov.quiet:
                sys.stdout.write("    " + line)
                sys.stdout.flush()
        rc = p.wait()
    text = read(out_dir / "run.log")
    if rc == 0:
        status = "ok"
    elif rc == 2 and "출력 불일치" in text:
        status = "output_mismatch"
    elif "서버가 종료" in text or "서버가 바로 종료" in text:
        status = "server_died"          # D4: 메모리 부족 종료도 결과로 기록
    else:
        status = f"failed(rc={rc})"
    anomalies = []
    if status == "output_mismatch":
        anomalies.append("출력 불일치")
    meta = {}
    try:
        meta = json.loads(read(out_dir / "meta.json") or "{}")
    except Exception:
        pass
    dm = meta.get("disk_measure", {})
    for k in ("read_limit_ok", "write_limit_ok"):
        if dm.get(k) is False:
            anomalies.append(f"io 제한 미적용 ({k}, 실측 {dm})")
    if a.get("max_freq") and meta.get("applied_max_freq_khz") and \
            int(meta["applied_max_freq_khz"]) != int(a["max_freq"]) * 1000:
        anomalies.append(f"클럭 제한 미적용 (요청 {a['max_freq']}MHz, 적용 {meta['applied_max_freq_khz']}kHz)")
    left = leftovers()
    if left:
        reset_limits()
        anomalies.append("정리 안 됨: " + "; ".join(left) + f" → reset 후 {leftovers() or '정상'}")
    row.update(status=status, rc=rc, minutes=round((time.time() - t0) / 60, 2),
               anomalies=" | ".join(anomalies), finished_at=dt.datetime.now().isoformat(timespec="seconds"))
    status_rows.append(row)
    log(f"=== {stage}/{name} 끝: {status}, {row['minutes']}분" + (f", 이상: {row['anomalies']}" if anomalies else ""))
    return "anomaly" if anomalies else status


# ---------------------------------------------------------------- 합치기

def cond_values(stage, cond, run_dir, status):
    meta = {}
    try:
        meta = json.loads(read(run_dir / "meta.json") or "{}")
    except Exception:
        pass
    a = meta.get("args", {})
    dm = meta.get("disk_measure", {})
    return {
        "stage": stage, "condition": cond.get("name", run_dir.name), "group": cond.get("group", ""),
        "status": status,
        "threads": a.get("threads", ""), "cores": len(_cpus(a.get("cpus"))) if a.get("cpus") else a.get("threads", ""),
        "max_freq": a.get("max_freq") or (int(meta.get("applied_max_freq_khz") or 0) // 1000 or ""),
        "cpu_quota": a.get("cpu_quota", ""), "mem_limit": a.get("mem_limit", ""),
        "mem_high": a.get("mem_high", ""), "swap_max": a.get("swap_max", "") if a.get("mem_limit") else "",
        "io_read": a.get("io_read", ""), "io_write": a.get("io_write", ""),
        "kv_dir": a.get("kv_dir", ""), "kv_fs": meta.get("kv_fs_type", ""),
        "disk_write_mb_per_s": dm.get("write_mb_per_s", ""), "disk_read_mb_per_s": dm.get("read_mb_per_s", ""),
        "disk_read_cache": dm.get("read_cache", ""),
        "_idle": meta.get("idle_rss_mb", {}), "_widle": meta.get("warm_idle_rss_mb", {}),
        "ctx": a.get("ctx", ""), "bench_repo_commit": meta.get("bench_repo_commit", "")[:9],
        "llama_cpp_commit": meta.get("llama_cpp_commit", "")[:9], "result_dir": str(run_dir),
    }


def _cpus(spec):
    out = set()
    for part in str(spec).split(","):
        lo, _, hi = part.partition("-")
        out.update(range(int(lo), int(hi or lo) + 1))
    return out


def merge(cfgs, out_root):
    out_root = Path(out_root).expanduser()
    all_rows, fields = [], None
    for cfg in cfgs:
        stage = cfg["stage"]
        sdir = out_root / stage
        status = {}
        st = sdir / "sweep_status.csv"
        if st.exists():
            for r in csv.DictReader(open(st)):
                status[r["condition"]] = r["status"]       # 마지막 실행 기준
        rows = []
        for cond in cfg["conditions"]:
            run_dir = sdir / cond["name"]
            summ = run_dir / "summary.csv"
            if not summ.exists():
                continue
            cv = cond_values(stage, cond, run_dir, status.get(cond["name"], ""))
            for r in csv.DictReader(open(summ)):
                c = {k: v for k, v in cv.items() if not k.startswith("_")}
                c["idle_rss_mb"] = cv["_idle"].get(r["model"], "")
                c["warm_idle_rss_mb"] = cv["_widle"].get(r["model"], "")
                rows.append({**c, **r})
                if fields is None:
                    fields = COND_FIELDS + list(r.keys())
        if rows:
            with open(sdir / "sweep_summary.csv", "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                w.writeheader()
                w.writerows(rows)
            log(f"합침: {sdir / 'sweep_summary.csv'} ({len(rows)}줄)")
        all_rows += rows
    if all_rows:
        # 단계를 모두 합친 파일 (이미 있는 다른 단계 결과도 포함되도록 전체 단계 디렉터리를 다시 읽음)
        every = []
        for sd in sorted(p for p in out_root.iterdir() if p.is_dir()):
            ss = sd / "sweep_summary.csv"
            if ss.exists():
                every += list(csv.DictReader(open(ss)))
        keys = fields + [k for r in every for k in r if k not in fields]
        keys = list(dict.fromkeys(keys))
        with open(out_root / "sweep_summary.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(every)
        log(f"전체 합침: {out_root / 'sweep_summary.csv'} ({len(every)}줄)")


def append_status(sdir, rows):
    if not rows:
        return
    path = sdir / "sweep_status.csv"
    fields = ["stage", "condition", "status", "rc", "minutes", "anomalies", "started_at", "finished_at",
              "result_dir", "cmd"]
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(description="조건 목록으로 run_bench.py 일괄 실행")
    p.add_argument("configs", nargs="+", help="조건 파일 (configs/phase2/D1.json 등)")
    p.add_argument("--out-root", default=str(HOME / "aiwork/results/phase2"))
    p.add_argument("--only", default="", help="이 조건 이름만 (쉼표)")
    p.add_argument("--lengths", default="", help="모든 조건의 길이를 덮어씀 (파일럿용)")
    p.add_argument("--repeats", type=int, default=0, help="모든 조건의 반복을 덮어씀 (파일럿용)")
    p.add_argument("--model", default="", choices=["", "qwen", "llama", "both"])
    p.add_argument("--python", default=str(HOME / "aiwork/venv/bin/python"))
    p.add_argument("--dry-run", action="store_true", help="실행할 명령만 출력")
    p.add_argument("--merge-only", action="store_true", help="실행 없이 summary.csv만 다시 합침")
    p.add_argument("--overwrite", action="store_true", help="이미 결과가 있는 조건도 다시 실행")
    p.add_argument("--keep-going", action="store_true", help="이상 징후가 있어도 다음 조건 진행")
    p.add_argument("--allow-dirty", action="store_true",
                   help="scripts/configs에 커밋 안 된 변경이 있어도 실행 (bench_repo_commit 추적이 깨짐)")
    p.add_argument("--quiet", action="store_true", help="run_bench 출력을 화면에 안 보임 (run.log에는 남음)")
    ov = p.parse_args()

    cfgs = [load_config(c) for c in ov.configs]
    only = {x.strip() for x in ov.only.split(",") if x.strip()}
    if only:
        known = {c["name"] for cfg in cfgs for c in cfg["conditions"]}
        if only - known:
            p.error(f"없는 조건 이름: {', '.join(sorted(only - known))}")
    if ov.merge_only:
        merge(cfgs, ov.out_root)
        return

    if not ov.dry_run:
        dirty = repo_dirty()
        if dirty and not ov.allow_dirty:
            sys.exit("scripts/ 또는 configs/에 커밋 안 된 변경이 있음. 측정 전에 커밋하세요 "
                     "(meta.json의 bench_repo_commit으로 추적하기 위해):\n" + dirty)

    t_all = time.time()
    stop = None
    for cfg in cfgs:
        sdir = Path(ov.out_root).expanduser() / cfg["stage"]
        status_rows = []
        for cond in cfg["conditions"]:
            if only and cond["name"] not in only:
                continue
            if not ov.dry_run:
                why = busy_reasons()
                if why:
                    stop = f"{cfg['stage']}/{cond['name']} 시작 전 다른 실험 감지 → 중단: " + "; ".join(why)
                    break
            r = run_condition(cfg, cond, ov, status_rows)
            if r in ("anomaly", "output_mismatch") and not ov.keep_going:
                stop = f"{cfg['stage']}/{cond['name']}에서 이상 징후 → 중단 (원인 확인 후 다시 실행)"
                break
        if not ov.dry_run:
            sdir.mkdir(parents=True, exist_ok=True)
            append_status(sdir, status_rows)
        if stop:
            break
    if not ov.dry_run:
        merge(cfgs, ov.out_root)
        left = leftovers()
        log(f"최종 정리 확인: {'정상' if not left else left}")
    log(f"sweep 전체 소요: {(time.time() - t_all) / 60:.1f}분")
    if stop:
        log(stop)
        sys.exit(3)


if __name__ == "__main__":
    main()
