#!/usr/bin/env python3
"""
KV Cache 저장·복원 vs 재계산 벤치마크.

llama-server의 슬롯 저장/복원 API로 KV Cache를 SSD에 저장했다가 다시 불러오고,
프롬프트를 처음부터 다시 처리(재계산)하는 경우와 시간을 비교한다.

조건 하나(모델, 길이 N, 반복 r)마다:
  1. 재계산      : 슬롯 비우기 -> 프롬프트 처리 (재계산 시간)
  2. RAW 저장    : 슬롯 저장 -> fsync (실제 디스크 쓰기까지)
  3. 기준 출력 A : 저장 직후의 KV 상태에서 생성
  4. RAW 복원    : cold(캐시 비움) / warm 각각 복원 -> 같은 요청 (출력 B, A와 비교)
  5. LZ4 저장    : RAW 파일을 LZ4로 압축 -> fsync, RAW 삭제
  6. LZ4 복원    : cold / warm 각각 압축 해제 -> 복원 -> 같은 요청

A와 B는 "KV 상태 + 마지막 토큰 1개 계산 + 생성"이라는 같은 경로를 거치므로,
복원이 정확하면 출력이 비트 단위로 같아야 한다. (프롬프트 전체를 다시 처리한
결과와 비교하면 배치 크기 차이로 생기는 미세한 수치 차이 때문에 다를 수 있다.)
결과는 조건마다 CSV 한 줄씩 바로 기록한다(중간에 멈춰도 그때까지 남음).

예시 (짧은 시험):
  ~/aiwork/venv/bin/python scripts/run_bench.py --model qwen --lengths 256,1024 --repeats 1
"""

import argparse
import csv
import datetime as dt
import json
import os
import platform
import re
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path.home()
REPO_ROOT = Path(__file__).resolve().parent.parent

MODELS = {
    "qwen": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
    "llama": "Llama-3.2-1B-Instruct-Q4_K_M.gguf",
}

CSV_FIELDS = [
    "model", "n_tokens", "rep", "storage", "cache",
    "recompute_prompt_n", "recompute_ms",
    "save_ms", "fsync_ms", "raw_bytes",
    "lz4_bytes", "compress_ms", "decompress_ms",
    "restore_ms", "n_restored",
    "resume_prompt_n", "resume_prompt_ms", "resume_total_ms",
    "speedup", "output_match",
    "t_start", "t_end",
    # 메모리 (llama-server의 /proc/<pid>/status, MiB). 기존 열 뒤에 붙여 하위 호환 유지
    "rss_after_prefill_mb", "rss_after_restore_mb",
    "swap_after_prefill_mb", "swap_after_restore_mb",
]


def log(msg):
    now = dt.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}", flush=True)


class ServerDied(RuntimeError):
    """실험 도중 llama-server가 종료됨 (메모리 제한 등)."""


UNITS = {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4}


def parse_size(s):
    """'2G', '768M', '1.5G', '1048576' → 바이트. 형식이 틀리면 None."""
    m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([KMGT]?)", s.strip(), re.I)
    if not m:
        return None
    return int(float(m.group(1)) * UNITS[m.group(2).upper()])


def human(n):
    for u in ("T", "G", "M", "K"):
        if n >= UNITS[u]:
            return f"{n / UNITS[u]:.1f}{u}"
    return f"{n}B"


def meminfo_bytes(key):
    for line in (read_text("/proc/meminfo") or "").splitlines():
        if line.startswith(key + ":"):
            return int(line.split()[1]) * 1024
    return 0


RAM_FS = {"tmpfs", "ramfs"}


def fs_type(path):
    """경로가 속한 파일시스템 종류 (/proc/mounts에서 가장 긴 마운트 지점). 경로가 아직 없어도 됨."""
    path = os.path.abspath(path)
    best, kind = "", ""
    for line in (read_text("/proc/mounts") or "").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        mnt = parts[1].replace("\\040", " ")
        if (path == mnt or path.startswith(mnt.rstrip("/") + "/")) and len(mnt) > len(best):
            best, kind = mnt, parts[2]
    return kind


def ms_since(t0):
    return (time.perf_counter() - t0) * 1000.0


# ---------------------------------------------------------------- HTTP

class Server:
    def __init__(self, port):
        self.base = f"http://127.0.0.1:{port}"

    def _req(self, method, path, body=None, timeout=3600):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {e.read().decode()[:500]}")

    def healthy(self):
        try:
            with urllib.request.urlopen(self.base + "/health", timeout=2) as r:
                return r.status == 200
        except Exception:
            return False

    def tokenize(self, text):
        return self._req("POST", "/tokenize", {"content": text})["tokens"]

    def completion(self, tokens, n_predict):
        return self._req("POST", "/completion", {
            "prompt": tokens, "n_predict": n_predict, "temperature": 0,
            "cache_prompt": True, "id_slot": 0,
        })

    def slot(self, action, filename=None):
        body = {"filename": filename} if filename else {}
        res = self._req("POST", f"/slots/0?action={action}", body)
        if isinstance(res, dict) and res.get("error"):
            raise RuntimeError(f"slot {action} 실패: {res['error']}")
        return res


def cgroup_props(args):
    """systemd-run -p 로 넘길 제한 목록 (관리자 권한 불필요)."""
    props = []
    if args.mem_limit:
        props += [f"MemoryMax={args.mem_limit}", f"MemorySwapMax={args.swap_max}"]
    if args.mem_high:
        props.append(f"MemoryHigh={args.mem_high}")
    if args.cpu_quota:
        props.append(f"CPUQuota={args.cpu_quota}")
    return props


# ---------------------------------------------------------------- 시스템 제한 (전용 sudo 명령)

HELPER_DIR = os.environ.get("KVB_HELPER_DIR", "/usr/local/sbin")   # 시험용으로만 바꿈
IO_CMD = f"{HELPER_DIR}/kvb-io-limit"
FREQ_CMD = f"{HELPER_DIR}/kvb-cpufreq"


def sudo_helper(cmd, *a, check=True):
    r = subprocess.run(["sudo", "-n", cmd, *a], capture_output=True, text=True)
    if r.returncode != 0 and check:
        raise RuntimeError(f"{cmd} {' '.join(a)} 실패: {(r.stderr or r.stdout).strip()}")
    return r


def reset_system_limits(quiet=False):
    """이전 실행이 남긴 디스크 속도·CPU 클럭 제한을 푼다. 실패해도 멈추지 않음."""
    for cmd in (IO_CMD, FREQ_CMD):
        if Path(cmd).exists():
            r = sudo_helper(cmd, "reset", check=False)
            if not quiet:
                log(f"해제: {(r.stdout or r.stderr).strip()}")


def apply_system_limits(args):
    if args.io_read or args.io_write:
        r = sudo_helper(IO_CMD, args.io_read or "-", args.io_write or "-")
        log(r.stdout.strip())
    if args.max_freq:
        r = sudo_helper(FREQ_CMD, str(args.max_freq))
        log(r.stdout.strip())


def port_in_use(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_server(args, model_path, raw_dir, out_dir, tag):
    cmd = [
        str(Path(args.llama_dir) / "build/bin/llama-server"),
        "-m", str(model_path), "-t", str(args.threads), "-c", str(args.ctx),
        "-np", "1", "--host", "127.0.0.1", "--port", str(args.port),
        "--slot-save-path", str(raw_dir) + "/",
    ]
    env = os.environ.copy()
    if args.cpus:
        # 지정한 CPU 코어에서만 실행 (예: 0-3)
        cmd = ["taskset", "-c", args.cpus] + cmd
    props = cgroup_props(args)
    if props:
        # cgroup v2로 llama-server 하나만 메모리·CPU 사용률 제한
        env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        cmd = ["systemd-run", "--user", "--scope", "--quiet"] + \
              [x for p in props for x in ("-p", p)] + cmd
    log_f = open(out_dir / f"server_{tag}.log", "w")
    log(f"서버 시작: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=log_f, stderr=subprocess.STDOUT, env=env,
                            start_new_session=True)
    srv = Server(args.port)
    t0 = time.time()
    while time.time() - t0 < args.server_timeout:
        if proc.poll() is not None:
            hint = (" 메모리 제한이 너무 작으면 모델을 올리다 종료됩니다."
                    if (args.mem_limit or args.mem_high) else "")
            raise RuntimeError(f"서버가 바로 종료됨 (exit {proc.returncode}). {log_f.name} 확인.{hint}")
        if srv.healthy():
            log(f"서버 준비 완료 ({time.time() - t0:.1f}s)")
            return proc, srv, log_f
        time.sleep(1)
    raise RuntimeError("서버 준비 시간 초과")


def stop_server(proc, log_f):
    if proc is None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=30)
    except Exception:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            pass
    if log_f:
        log_f.close()


# ---------------------------------------------------------------- 메모리 (RSS)

def proc_comm(pid):
    return read_text(f"/proc/{pid}/comm")


def find_server_pid(proc):
    """실제 llama-server PID. taskset·systemd-run --scope는 exec로 자신을 바꾸므로 보통
    proc.pid와 같지만, 아니면 자식 프로세스를 따라가며 찾는다."""
    if proc is None:
        return None
    todo = [proc.pid]
    while todo:
        pid = todo.pop(0)
        if proc_comm(pid).startswith("llama-server"):
            return pid
        kids = read_text(f"/proc/{pid}/task/{pid}/children").split()
        todo += [int(k) for k in kids]
    return None


def proc_status_mb(pid, key):
    """/proc/<pid>/status 의 VmRSS·VmSwap 등 (kB) → MiB. 못 읽으면 빈칸."""
    if not pid:
        return ""
    for line in read_text(f"/proc/{pid}/status").splitlines():
        if line.startswith(key + ":"):
            return round(int(line.split()[1]) / 1024, 1)
    return ""


# ---------------------------------------------------------------- 파일, 캐시

def fsync_file(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def evict(path, method):
    """cold 조건 만들기: 파일이 RAM(페이지 캐시)에 남지 않게 한다."""
    if method == "drop":
        subprocess.run(["sudo", "-n", "/usr/local/sbin/kvb-drop-caches"], check=True)
    else:  # fadvise: 그 파일만 캐시에서 내림 (sudo 불필요)
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        finally:
            os.close(fd)


def measure_disk(args):
    """kv-dir에서 순차 쓰기(+fsync)·읽기(cold) 속도를 잰다. 제한을 건 뒤 부르므로
    io 제한이 실제로 적용됐는지도 확인된다. MB = 10^6 바이트."""
    kv = Path(args.kv_dir)
    kv.mkdir(parents=True, exist_ok=True)
    path = kv / "_measure_disk.bin"
    size = args.measure_disk_mb * UNITS["M"]
    chunk = os.urandom(UNITS["M"])
    res = {"path": str(path), "size_bytes": size, "block_bytes": UNITS["M"]}
    try:
        t0 = time.perf_counter()
        with open(path, "wb") as f:
            for _ in range(args.measure_disk_mb):
                f.write(chunk)
            f.flush()
            os.fsync(f.fileno())
        w_s = ms_since(t0) / 1000
        cold = "cold" in args.cache
        if cold:
            evict(path, args.evict)
        t0 = time.perf_counter()
        with open(path, "rb", buffering=0) as f:
            while f.read(UNITS["M"]):
                pass
        r_s = ms_since(t0) / 1000
        res.update(write_mb_per_s=round(size / 1e6 / w_s, 2), read_mb_per_s=round(size / 1e6 / r_s, 2),
                   read_cache="cold" if cold else "warm")
    finally:
        path.unlink(missing_ok=True)
    # 제한을 걸었다면 실제로 걸렸는지 (측정값이 상한보다 15% 넘게 빠르면 적용 안 된 것으로 봄)
    for kind, lim in (("read", args.io_read), ("write", args.io_write)):
        if lim:
            lim_mb = parse_size(lim) / 1e6
            ok = res[f"{kind}_mb_per_s"] <= lim_mb * 1.15
            res[f"{kind}_limit_mb_per_s"] = round(lim_mb, 2)
            res[f"{kind}_limit_ok"] = ok
            if not ok:
                log(f"경고: {kind} 제한 {lim}({lim_mb:.1f}MB/s)인데 실측 {res[f'{kind}_mb_per_s']}MB/s. "
                    "제한이 적용되지 않은 것 같습니다")
    log(f"저장장치 실측 ({args.kv_dir}, {args.measure_disk_mb}MiB): 쓰기 {res['write_mb_per_s']} MB/s, "
        f"읽기({res['read_cache']}) {res['read_mb_per_s']} MB/s")
    return res


def lz4_compress(src, dst):
    import lz4.frame
    t0 = time.perf_counter()
    with open(src, "rb") as f:
        data = f.read()
    comp = lz4.frame.compress(data)
    with open(dst, "wb") as f:
        f.write(comp)
        f.flush()
        os.fsync(f.fileno())
    return ms_since(t0), len(comp)


def lz4_decompress(src, dst):
    import lz4.frame
    t0 = time.perf_counter()
    with open(src, "rb") as f:
        comp = f.read()
    data = lz4.frame.decompress(comp)
    with open(dst, "wb") as f:
        f.write(data)
    return ms_since(t0)


# ---------------------------------------------------------------- 메타, 모니터링

def run_cmd(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def read_text(path):
    try:
        return Path(path).read_text().strip()
    except Exception:
        return ""


def collect_meta(args):
    cpu = ""
    for line in read_text("/proc/cpuinfo").splitlines():
        if line.startswith("model name"):
            cpu = line.split(":", 1)[1].strip()
            break
    return {
        "started_at": dt.datetime.now().isoformat(timespec="seconds"),
        "hostname": socket.gethostname(),
        "kernel": platform.release(),
        "os": read_text("/etc/os-release").split("\n")[0] if read_text("/etc/os-release") else "",
        "cpu": cpu,
        "cpu_governor": read_text("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"),
        "intel_no_turbo": read_text("/sys/devices/system/cpu/intel_pstate/no_turbo"),
        "mem_total": next((l for l in read_text("/proc/meminfo").splitlines()
                           if l.startswith("MemTotal")), ""),
        "swap": run_cmd(["swapon", "--show"]),
        "disks": run_cmd(["lsblk", "-o", "NAME,SIZE,MODEL,MOUNTPOINTS"]),
        "llama_cpp_commit": run_cmd(["git", "-C", args.llama_dir, "rev-parse", "HEAD"]),
        "bench_repo_commit": run_cmd(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"]),
        "model_sha256": read_text(Path(args.models_dir) / "SHA256SUMS"),
        "python": sys.version.split()[0],
        "cpu_count": os.cpu_count(),
        "args": vars(args),
    }


def start_monitors(out_dir):
    procs = []
    if shutil.which("iostat"):
        f = open(out_dir / "iostat.log", "w")
        procs.append((subprocess.Popen(["iostat", "-x", "-m", "-t", "1"], stdout=f,
                                       stderr=subprocess.DEVNULL), f))
    if shutil.which("vmstat"):
        f = open(out_dir / "vmstat.log", "w")
        procs.append((subprocess.Popen(["vmstat", "-t", "1"], stdout=f,
                                       stderr=subprocess.DEVNULL), f))
    return procs


def stop_monitors(procs):
    for p, f in procs:
        p.terminate()
        try:
            p.wait(timeout=5)
        except Exception:
            p.kill()
        f.close()


# ---------------------------------------------------------------- 측정

def resume(srv, tokens, args, ref_content):
    """복원된 슬롯으로 같은 요청을 보내고 결과를 확인한다."""
    res = srv.completion(tokens, args.n_predict)
    t = res.get("timings", {})
    return t.get("prompt_n"), t.get("prompt_ms"), res.get("content") == ref_content


def bench_model(args, key, writer, csv_f, out_dir, progress, meta=None):
    model_path = Path(args.models_dir) / MODELS[key]
    raw_dir = Path(args.kv_dir) / "raw"
    lz4_dir = Path(args.kv_dir) / "lz4"
    raw_dir.mkdir(parents=True, exist_ok=True)
    lz4_dir.mkdir(parents=True, exist_ok=True)

    proc = log_f = None
    if not args.no_server:
        proc, srv, log_f = start_server(args, model_path, raw_dir, out_dir, key)
    else:
        srv = Server(args.port)
        if not srv.healthy():
            raise RuntimeError(f"--no-server인데 {args.port} 포트에 서버가 없음")

    pid = find_server_pid(proc)
    if meta is not None:
        # 대화 없음(서버 시작 직후) RSS. 이후 증가량의 기준값
        meta.setdefault("server_pid", {})[key] = pid
        meta.setdefault("idle_rss_mb", {})[key] = proc_status_mb(pid, "VmRSS")
        (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        log(f"[{key}] 서버 PID {pid}, 대화 없음 RSS {meta['idle_rss_mb'][key]} MiB")

    try:
        corpus = Path(args.corpus).read_text(encoding="utf-8", errors="ignore")
        all_tokens = srv.tokenize(corpus)
        need = max(args.lengths)
        if len(all_tokens) < need:
            log(f"경고: 재료 토큰 {len(all_tokens)}개 < 필요 {need}개, 재료를 반복해서 씀")
            all_tokens = (all_tokens * (need // len(all_tokens) + 1))
        log(f"[{key}] 재료 토큰 {len(all_tokens)}개")

        # 워밍업: 서버를 켠 뒤 첫 요청은 메모리 할당 등으로 느려서 측정에서 제외
        for _ in range(args.warmup):
            srv.slot("erase")
            srv.completion(all_tokens[:min(512, max(args.lengths))], 4)
        srv.slot("erase")
        if args.warmup:
            log(f"[{key}] 워밍업 {args.warmup}회 완료")
        if meta is not None:
            meta.setdefault("warm_idle_rss_mb", {})[key] = proc_status_mb(pid, "VmRSS")
            (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))

        for n in args.lengths:
            tokens = all_tokens[:n]
            for rep in range(1, args.repeats + 1):
                if proc is not None and proc.poll() is not None:
                    raise ServerDied(server_died_msg(args, proc))
                progress["done"] += 1
                log(f"[{progress['done']}/{progress['total']}] {key} N={n} rep={rep}")
                fname = f"kv_{key}_N{n}_r{rep}.bin"
                raw_path = raw_dir / fname
                lz4_path = lz4_dir / (fname + ".lz4")

                # 1. 재계산: 프롬프트 처리 시간 (생성은 1토큰만)
                srv.slot("erase")
                a = srv.completion(tokens, 1)
                ta = a.get("timings", {})
                base = {
                    "model": key, "n_tokens": n, "rep": rep,
                    "recompute_prompt_n": ta.get("prompt_n"),
                    "recompute_ms": round(ta.get("prompt_ms", 0), 3),
                    "rss_after_prefill_mb": proc_status_mb(pid, "VmRSS"),
                    "swap_after_prefill_mb": proc_status_mb(pid, "VmSwap"),
                }

                # 2. RAW 저장 (+ fsync로 실제 디스크 쓰기까지)
                s = srv.slot("save", fname)
                t0 = time.perf_counter()
                fsync_file(raw_path)
                base["fsync_ms"] = round(ms_since(t0), 3)
                base["save_ms"] = round(s.get("timings", {}).get("save_ms", 0), 3)
                base["raw_bytes"] = raw_path.stat().st_size

                # 3. 기준 출력 A: 저장한 것과 같은 KV 상태에서 생성
                ref = srv.completion(tokens, args.n_predict).get("content")

                def record(storage, cache, extra, restore_res, t_start):
                    # 복원 직후 (이어서 생성하기 전) 메모리
                    mem = {"rss_after_restore_mb": proc_status_mb(pid, "VmRSS"),
                           "swap_after_restore_mb": proc_status_mb(pid, "VmSwap")}
                    pn, pms, match = resume(srv, tokens, args, ref)
                    restore_ms = restore_res.get("timings", {}).get("restore_ms", 0)
                    total = restore_ms + (pms or 0) + extra.get("decompress_ms", 0)
                    row = dict(base, storage=storage, cache=cache,
                               restore_ms=round(restore_ms, 3),
                               n_restored=restore_res.get("n_restored"),
                               resume_prompt_n=pn, resume_prompt_ms=round(pms or 0, 3),
                               resume_total_ms=round(total, 3),
                               speedup=round(base["recompute_ms"] / total, 2) if total else "",
                               output_match=match,
                               t_start=round(t_start, 3), t_end=round(time.time(), 3),
                               **mem,
                               **{k: round(v, 3) if isinstance(v, float) else v
                                  for k, v in extra.items()})
                    writer.writerow(row)
                    csv_f.flush()
                    flag = "" if match else "  <-- 출력 불일치!"
                    log(f"    {storage:3s} {cache:4s}: 복원 {total:8.1f} ms vs 재계산 "
                        f"{base['recompute_ms']:8.1f} ms (x{row['speedup']}){flag}")

                # 3. RAW 복원
                if "raw" in args.storage:
                    for cache in args.cache:
                        t_start = time.time()
                        srv.slot("erase")
                        if cache == "cold":
                            evict(raw_path, args.evict)
                        r = srv.slot("restore", fname)
                        record("raw", cache, {}, r, t_start)

                # 4~5. LZ4
                if "lz4" in args.storage:
                    comp_ms, comp_bytes = lz4_compress(raw_path, lz4_path)
                    raw_path.unlink()
                    lz4_extra = {"lz4_bytes": comp_bytes, "compress_ms": comp_ms}
                    for cache in args.cache:
                        t_start = time.time()
                        srv.slot("erase")
                        if cache == "cold":
                            evict(lz4_path, args.evict)
                        dec_ms = lz4_decompress(lz4_path, raw_path)
                        r = srv.slot("restore", fname)
                        record("lz4", cache, dict(lz4_extra, decompress_ms=dec_ms), r, t_start)
                        raw_path.unlink()

                for p in (raw_path, lz4_path):
                    if p.exists():
                        p.unlink()
    except ServerDied:
        raise
    except Exception as e:
        # 요청이 실패했는데 서버가 죽어 있으면, 원인을 알아보기 쉽게 바꿔서 알림
        time.sleep(1)
        if proc is not None and proc.poll() is not None:
            raise ServerDied(server_died_msg(args, proc)) from e
        raise
    finally:
        stop_server(proc, log_f)
        for d in (raw_dir, lz4_dir):          # 중간에 멈춰도 실험 SSD에 파일을 남기지 않음
            for f in d.glob(f"kv_{key}_*"):
                f.unlink(missing_ok=True)


def server_died_msg(args, proc):
    code = proc.returncode
    why = ""
    if code in (-9, 137):
        why = " 강제 종료(SIGKILL)라 메모리 부족 가능성이 큽니다."
    if args.mem_limit or args.mem_high:
        why += f" 메모리 상한={args.mem_limit or '-'}, 완만한 상한={args.mem_high or '-'} 을 늘려 보세요."
    return f"실험 도중 서버가 종료됨 (exit {code}).{why} 그때까지의 결과는 저장되어 있습니다."


SUMMARY_FIELDS = [
    # 기존 열 (순서 유지)
    "model", "n_tokens", "storage", "cache", "runs", "recompute_ms_mean", "resume_total_ms_mean",
    "speedup_mean", "raw_bytes", "lz4_bytes", "all_match",
    # 2차 실험에서 추가 (뒤에만 붙임)
    "recompute_ms_std", "resume_total_ms_std", "restore_ms_mean", "restore_ms_std",
    "save_total_ms_mean", "save_total_ms_std", "breakeven_reuse",
    "prefill_tok_per_s", "load_mb_per_s",
    "rss_after_prefill_mb_mean", "rss_after_restore_mb_mean",
    "swap_after_prefill_mb_max", "swap_after_restore_mb_max",
]


def _floats(rows, key):
    out = []
    for r in rows:
        try:
            out.append(float(r[key]))
        except (KeyError, TypeError, ValueError):
            pass
    return out


def _mean(xs):
    return statistics.mean(xs) if xs else None


def _std(xs):
    return statistics.stdev(xs) if len(xs) >= 2 else None


def _fmt(x, nd=3):
    return "" if x is None else f"{x:.{nd}f}"


def summarize(csv_path):
    """results.csv → summary.csv (조건별 평균). 단위: ms, 바이트, 토큰/s, MB/s(10^6), MiB."""
    rows = list(csv.DictReader(open(csv_path)))
    if not rows:
        return
    groups = {}
    for r in rows:
        k = (r["model"], int(r["n_tokens"]), r["storage"], r["cache"])
        groups.setdefault(k, []).append(r)
    out = []
    print("\n=== 요약 (평균) ===", flush=True)
    print(f"{'model':6s} {'N':>6s} {'stor':4s} {'cache':5s} {'재계산ms':>10s} "
          f"{'복원ms':>9s} {'배율':>6s} {'일치':>4s}")
    for k in sorted(groups):
        g = groups[k]
        rec_l, res_l = _floats(g, "recompute_ms"), _floats(g, "resume_total_ms")
        rec, res = statistics.mean(rec_l), statistics.mean(res_l)
        sp = rec / res if res else 0
        match = all(x["output_match"] == "True" for x in g)
        lz = g[0].get("lz4_bytes", "")
        raw_b = float(g[0]["raw_bytes"])
        save_l = [a + b for a, b in zip(_floats(g, "save_ms"), _floats(g, "fsync_ms"))]
        save = _mean(save_l)
        restore_l = _floats(g, "restore_ms")
        restore = _mean(restore_l)
        # 저장 1번을 몇 번 재사용해야 본전인가: (저장 + 복원) / (재계산 - 복원). 복원이 더 느리면 빈칸
        be = (save + res) / (rec - res) if (save is not None and rec > res) else None
        # 파일 읽기 속도는 RAW cold에서만 의미 있음 (LZ4는 압축 해제한 파일을 읽고, warm은 RAM)
        load = (raw_b / 1e6) / (restore / 1000) if (k[2] == "raw" and k[3] == "cold" and restore) else None
        swp_p, swp_r = _floats(g, "swap_after_prefill_mb"), _floats(g, "swap_after_restore_mb")
        print(f"{k[0]:6s} {k[1]:6d} {k[2]:4s} {k[3]:5s} {rec:10.1f} {res:9.1f} "
              f"{sp:6.1f} {'O' if match else 'X':>4s}")
        out.append([
            k[0], k[1], k[2], k[3], len(g), f"{rec:.3f}", f"{res:.3f}", f"{sp:.2f}",
            g[0]["raw_bytes"], lz, match,
            _fmt(_std(rec_l)), _fmt(_std(res_l)), _fmt(restore), _fmt(_std(restore_l)),
            _fmt(save), _fmt(_std(save_l)), _fmt(be, 4),
            _fmt(k[1] / rec * 1000 if rec else None, 2), _fmt(load, 2),
            _fmt(_mean(_floats(g, "rss_after_prefill_mb")), 1),
            _fmt(_mean(_floats(g, "rss_after_restore_mb")), 1),
            _fmt(max(swp_p) if swp_p else None, 1), _fmt(max(swp_r) if swp_r else None, 1),
        ])
    with open(csv_path.parent / "summary.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(SUMMARY_FIELDS)
        w.writerows(out)


# ---------------------------------------------------------------- main

def parse_args():
    ncpu = os.cpu_count() or 8
    p = argparse.ArgumentParser(description="KV Cache 저장·복원 vs 재계산 벤치마크")
    # 기본
    p.add_argument("--model", default="qwen", choices=["qwen", "llama", "both"])
    p.add_argument("--lengths", default="16,32,64,128,256,512,1024,2048,4096",
                   help="프롬프트 토큰 수, 쉼표로 구분 (각 1~16384)")
    p.add_argument("--repeats", type=int, default=5, help="조건당 반복 횟수 (1~1000)")
    # CPU
    p.add_argument("--threads", type=int, default=ncpu, help=f"llama.cpp 스레드 수 (1~{ncpu})")
    p.add_argument("--cores", type=int, default=0, help=f"사용할 CPU 코어 개수 (1~{ncpu}, 0이면 전체)")
    p.add_argument("--cpus", default="", help="코어 번호를 직접 지정 (예: 0-3). --cores 대신 쓸 때만")
    p.add_argument("--max-freq", default="", help="CPU 최대 클럭 MHz, 예: 2400 (관리자 명령 사용)")
    p.add_argument("--cpu-quota", default="", help=f"CPU 사용률 상한 10%%~{ncpu * 100}%%, 예: 300%%")
    # 메모리
    p.add_argument("--mem-limit", default="", help="메모리 상한 256M~RAM, 예: 2G (비우면 제한 없음)")
    p.add_argument("--mem-high", default="", help="완만한 메모리 상한 256M~, 예: 1G (넘으면 느려짐)")
    p.add_argument("--swap-max", default="0", help="메모리 상한 걸 때 swap 허용량 0~swap 크기, 또는 infinity")
    # 디스크
    p.add_argument("--io-read", default="", help="실험 SSD 읽기 속도 상한 5M~2G, 예: 100M")
    p.add_argument("--io-write", default="", help="실험 SSD 쓰기 속도 상한 5M~2G, 예: 50M")
    # 측정 방식
    p.add_argument("--storage", default="raw,lz4", help="raw, lz4 중 선택 (쉼표)")
    p.add_argument("--cache", default="cold,warm", help="cold, warm 중 선택 (쉼표)")
    p.add_argument("--evict", default="drop", choices=["drop", "fadvise"],
                   help="cold 만드는 방법: drop(전체 캐시 비우기, sudo) / fadvise(해당 파일만)")
    p.add_argument("--n-predict", type=int, default=32, help="출력 비교용 생성 토큰 수 (1~256)")
    p.add_argument("--warmup", type=int, default=2, help="측정 전 워밍업 요청 횟수 (0~20)")
    # 예전 방식 (손으로 돌릴 때 호환용)
    p.add_argument("--advanced", default="",
                   help="한 줄 설정: cpu_quota=150%%,mem_high=1G,io_read=100M,io_write=100M,max_freq=2400")
    # 경로·기타
    p.add_argument("--ctx", type=int, default=0, help="컨텍스트 크기 (0이면 자동)")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--out", default="", help="결과 폴더 (기본: ~/aiwork/results/날짜_시각)")
    p.add_argument("--llama-dir", default=str(HOME / "aiwork/llama.cpp"))
    p.add_argument("--models-dir", default=str(HOME / "aiwork/models"))
    p.add_argument("--kv-dir", default="/mnt/ssd/kvcache")
    p.add_argument("--corpus", default=str(REPO_ROOT / "prompts/corpus.txt"))
    p.add_argument("--server-timeout", type=int, default=300)
    p.add_argument("--no-server", action="store_true",
                   help="서버를 띄우지 않고 이미 켜진 서버 사용 (디버깅용)")
    p.add_argument("--no-monitor", action="store_true", help="iostat/vmstat 기록 끄기")
    p.add_argument("--measure-disk", action="store_true",
                   help="시작할 때 kv-dir의 순차 쓰기·읽기 속도를 재서 meta.json에 기록 (제한 적용 확인용)")
    p.add_argument("--measure-disk-mb", type=int, default=256, help="--measure-disk 파일 크기 MiB (16~4096)")
    a = p.parse_args()
    errors = []

    def err(msg):
        errors.append(msg)

    # ---- 기본
    try:
        a.lengths = sorted({int(x) for x in a.lengths.split(",") if x.strip()})
    except ValueError:
        p.error("프롬프트 길이는 숫자를 쉼표로 (예: 16,32,1024)")
    if not a.lengths or not all(1 <= n <= 16384 for n in a.lengths):
        err("프롬프트 길이는 각각 1~16384")
    if not 1 <= a.repeats <= 1000:
        err("반복 횟수는 1~1000")

    # ---- 예전 한 줄 설정 → 개별 옵션 (개별 칸이 비어 있을 때만 채움)
    adv_keys = {"cpu_quota", "mem_high", "io_read", "io_write", "max_freq"}
    for item in [x.strip() for x in a.advanced.replace(" ", "").split(",") if x.strip()]:
        if "=" not in item:
            p.error(f"고급 설정 형식 오류: '{item}' (키=값)")
        k, v = item.split("=", 1)
        if k not in adv_keys:
            p.error(f"고급 설정에 없는 키: '{k}' (가능: {', '.join(sorted(adv_keys))})")
        if not str(getattr(a, k)).strip():
            setattr(a, k, v)

    for name in ("cpus", "max_freq", "cpu_quota", "mem_limit", "mem_high", "swap_max", "io_read", "io_write"):
        setattr(a, name, str(getattr(a, name)).strip())

    # ---- CPU
    if not 1 <= a.threads <= ncpu:
        err(f"스레드 수는 1~{ncpu}")
    if a.cores and a.cpus:
        err("코어 개수(--cores)와 코어 번호(--cpus)는 하나만")
    if a.cores:
        if not 1 <= a.cores <= ncpu:
            err(f"코어 개수는 1~{ncpu}")
        elif a.cores < ncpu:
            a.cpus = f"0-{a.cores - 1}" if a.cores > 1 else "0"
    if a.cpus and not re.fullmatch(r"[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*", a.cpus):
        err("코어 번호 형식 예: 0-3 또는 0,2,4")
    elif a.cpus and any(int(x) >= ncpu for x in re.findall(r"[0-9]+", a.cpus)):
        err(f"코어 번호는 0~{ncpu - 1}")
    if a.max_freq:
        if not re.fullmatch(r"[0-9]{3,5}", a.max_freq):
            err("CPU 최대 클럭은 MHz 숫자 (예: 2400)")
        else:
            lo = read_text("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_min_freq")
            hi = read_text("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq")
            if lo and hi and not int(lo) // 1000 <= int(a.max_freq) <= int(hi) // 1000:
                err(f"CPU 최대 클럭은 {int(lo) // 1000}~{int(hi) // 1000} MHz")
    if a.cpu_quota:
        m = re.fullmatch(r"([0-9]+)%?", a.cpu_quota)
        if not m or not 10 <= int(m.group(1)) <= ncpu * 100:
            err(f"CPU 사용률 상한은 10%~{ncpu * 100}%")
        else:
            a.cpu_quota = f"{int(m.group(1))}%"

    # ---- 메모리
    ram = meminfo_bytes("MemTotal") or 2 ** 62
    swap_total = meminfo_bytes("SwapTotal")
    min_mem = 256 * UNITS["M"]
    if a.mem_limit.lower() in ("0", "none"):
        a.mem_limit = ""
    mem_b = {}
    for name, label in (("mem_limit", "메모리 상한"), ("mem_high", "완만한 메모리 상한")):
        v = getattr(a, name)
        if not v:
            continue
        b = parse_size(v)
        if b is None:
            err(f"{label} 형식 예: 2G, 768M")
        elif not min_mem <= b <= ram:
            err(f"{label}은 256M~{human(ram)} (입력: {v})")
        else:
            mem_b[name] = b
    if "mem_limit" in mem_b and "mem_high" in mem_b and mem_b["mem_high"] >= mem_b["mem_limit"]:
        err("완만한 메모리 상한은 메모리 상한보다 작아야 함")
    a.swap_max = a.swap_max or "0"
    if a.swap_max.lower() == "infinity":
        a.swap_max = "infinity"
    else:
        b = parse_size(a.swap_max)
        if b is None:
            err("swap 허용량 형식 예: 0, 1G, infinity")
        elif b > (swap_total or ram):
            err(f"swap 허용량은 0~{human(swap_total or ram)} (PC의 swap 크기), 또는 infinity")

    # ---- 디스크
    for name, label in (("io_read", "SSD 읽기 속도 상한"), ("io_write", "SSD 쓰기 속도 상한")):
        v = getattr(a, name)
        if not v:
            continue
        m = re.fullmatch(r"([0-9]+)([KMG])", v.upper())
        b = parse_size(v)
        if not m or b is None:
            err(f"{label} 형식 예: 100M, 50M, 1G")
        elif not 5 * UNITS["M"] <= b <= 2 * UNITS["G"]:
            err(f"{label}은 5M~2G (입력: {v})")
        else:
            setattr(a, name, m.group(1) + m.group(2))

    # ---- 측정 방식
    a.storage = [x.strip() for x in a.storage.split(",") if x.strip()]
    a.cache = [x.strip() for x in a.cache.split(",") if x.strip()]
    if not a.storage or not set(a.storage) <= {"raw", "lz4"}:
        err("저장 방식은 raw, lz4")
    if not a.cache or not set(a.cache) <= {"cold", "warm"}:
        err("캐시 조건은 cold, warm")
    if not 1 <= a.n_predict <= 256:
        err("출력 비교용 생성 토큰 수는 1~256")
    if not 0 <= a.warmup <= 20:
        err("워밍업 횟수는 0~20")
    if not 16 <= a.measure_disk_mb <= 4096:
        err("--measure-disk-mb 는 16~4096")
    # RAM 디스크(tmpfs): 파일이 항상 RAM에 있어 cold가 없고, 디스크 속도 제한도 걸리지 않음
    a.kv_fs = fs_type(a.kv_dir)
    if a.kv_fs in RAM_FS:
        if a.io_read or a.io_write:
            err(f"kv-dir({a.kv_dir})가 RAM 디스크({a.kv_fs})라 SSD 읽기·쓰기 상한을 같이 쓸 수 없음")
        elif "cold" in a.cache:
            a.cache = [c for c in a.cache if c != "cold"] or ["warm"]
            print(f"경고: kv-dir({a.kv_dir})가 RAM 디스크({a.kv_fs})라 cold는 의미가 없어 warm만 측정합니다",
                  flush=True)

    if errors:
        p.exit(2, "입력값 오류 (실험을 시작하지 않음):\n  - " + "\n  - ".join(errors) + "\n")

    if a.cpus and a.threads > len(cpu_list(a.cpus)):
        log(f"경고: 스레드 {a.threads}개 > 코어 {len(cpu_list(a.cpus))}개. 스레드끼리 코어를 나눠 써서 느려집니다")
    if a.swap_max != "0" and not a.mem_limit:
        log("참고: swap 허용량은 메모리 상한을 걸었을 때만 적용됩니다 (지금은 무시)")
    if not a.ctx:
        a.ctx = max(a.lengths) + a.n_predict + 64
    if not a.out:
        a.out = str(HOME / "aiwork/results" / dt.datetime.now().strftime("%Y%m%d_%H%M%S"))
    return a


def cpu_list(spec):
    out = set()
    for part in spec.split(","):
        lo, _, hi = part.partition("-")
        out.update(range(int(lo), int(hi or lo) + 1))
    return out


def main():
    args = parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    models = ["qwen", "llama"] if args.model == "both" else [args.model]

    if not args.no_server and port_in_use(args.port):
        sys.exit(f"{args.port} 포트를 이미 누가 쓰고 있음. `pgrep -a llama` 로 남은 서버를 확인하세요.")
    if "lz4" in args.storage:
        import lz4.frame  # noqa: F401  (없으면 여기서 바로 실패)
    if cgroup_props(args):
        env = dict(os.environ, XDG_RUNTIME_DIR=os.environ.get("XDG_RUNTIME_DIR",
                                                              f"/run/user/{os.getuid()}"))
        chk = subprocess.run(["systemd-run", "--user", "--scope", "--quiet", "true"],
                             capture_output=True, text=True, env=env)
        if chk.returncode != 0:
            sys.exit("메모리·CPU 제한을 쓸 수 없음 (systemd-run --user 실패). "
                     "공용 PC에서 `sudo loginctl enable-linger ondevice-ai` 를 한 번 실행했는지 확인하세요.\n"
                     + chk.stderr.strip())
    if args.mem_limit and args.swap_max != "0":
        swaps = run_cmd(["swapon", "--show", "--noheadings", "--raw"])
        if not swaps:
            log("경고: swap이 꺼져 있어 swap 허용이 의미 없음")
        else:
            swap_path = swaps.split()[0]
            kv_root = "/" + "/".join(Path(args.kv_dir).parts[1:3])   # 예: /mnt/ssd
            if not swap_path.startswith(kv_root):
                log(f"경고: swap이 실험 SSD가 아닌 곳에 있음 ({swap_path}). "
                    "swap I/O가 실험 SSD가 아닌 디스크에서 발생합니다")
    for cmd, used in ((IO_CMD, args.io_read or args.io_write), (FREQ_CMD, args.max_freq)):
        if used and not Path(cmd).exists():
            sys.exit(f"{cmd} 가 없음. docs/SETUP.md 의 전용 명령 설치를 먼저 하세요.")
    log(f"조건: model={args.model} lengths={','.join(map(str, args.lengths))} repeats={args.repeats}")
    log(f"  CPU   : threads={args.threads} cores={args.cpus or '전체'} "
        f"max_freq={args.max_freq + 'MHz' if args.max_freq else '없음'} cpu_quota={args.cpu_quota or '없음'}")
    log(f"  메모리: mem_limit={args.mem_limit or '없음'} mem_high={args.mem_high or '없음'} "
        f"swap_max={args.swap_max if args.mem_limit else '-'}")
    log(f"  디스크: io_read={args.io_read or '없음'} io_write={args.io_write or '없음'}")
    log(f"  측정  : storage={','.join(args.storage)} cache={','.join(args.cache)} "
        f"evict={args.evict} n_predict={args.n_predict} warmup={args.warmup}")

    # Actions에서 취소(SIGTERM)해도 finally가 돌아 제한이 풀리도록
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))

    csv_path = out_dir / "results.csv"
    monitors = []
    t_all = time.time()
    reset_system_limits(quiet=True)      # 이전 실행이 남긴 제한 정리
    failed = None
    try:
        apply_system_limits(args)
        meta = collect_meta(args)
        meta["applied_max_freq_khz"] = read_text("/sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq")
        meta["kv_fs_type"] = args.kv_fs
        if args.measure_disk:
            meta["disk_measure"] = measure_disk(args)
        (out_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
        log(f"결과 폴더: {out_dir}")

        monitors = [] if args.no_monitor else start_monitors(out_dir)
        progress = {"done": 0, "total": len(models) * len(args.lengths) * args.repeats}
        with open(csv_path, "w", newline="") as csv_f:
            writer = csv.DictWriter(csv_f, fieldnames=CSV_FIELDS, extrasaction="ignore")
            writer.writeheader()
            for key in models:
                bench_model(args, key, writer, csv_f, out_dir, progress, meta)
    except RuntimeError as e:          # 서버 시작 실패, 실험 중 서버 종료, 제한 적용 실패 등
        failed = str(e)
    finally:
        stop_monitors(monitors)
        if args.io_read or args.io_write or args.max_freq:
            reset_system_limits()
    log(f"전체 소요: {(time.time() - t_all) / 60:.1f}분")
    if csv_path.exists():
        summarize(csv_path)
    if failed:
        log(f"오류로 중단: {failed}")
        sys.exit(1)

    mismatches = sum(1 for r in csv.DictReader(open(csv_path)) if r["output_match"] != "True")
    if mismatches:
        log(f"주의: 출력 불일치 {mismatches}건")
        sys.exit(2)


if __name__ == "__main__":
    main()
