# 공용 PC 구성 (재현용)

`scripts/run_bench.py`가 가정하는 공용 PC 설정. 2026-11-10에 공용 PC에서 확인한 실제 상태를 적었다.
새 PC에서 같은 실험을 하려면 아래를 순서대로 맞춘다. **이미 구성된 공용 PC에서는 다시 실행하지 않는다** (설정이 바뀌면 이전 결과와 비교할 수 없게 된다).

## 1. 장비와 경로

| 구분 | 값 |
| --- | --- |
| CPU | Intel Core i7-9700K (8코어 8스레드) |
| 메모리 | 32GB |
| OS SSD | WD Blue 250GB SATA (`/`) |
| 실험 SSD | Samsung 840 PRO 128GB SATA, ext4, `/mnt/ssd` |
| OS | Ubuntu Server 26.04.1 LTS, 사용자 `ondevice-ai` |

| 경로 | 내용 |
| --- | --- |
| `~/aiwork/llama.cpp` | llama.cpp, 커밋 `85cc432e2`, CPU 빌드 (`build/bin/llama-server`) |
| `~/aiwork/models` | GGUF 모델 2개와 `SHA256SUMS` |
| `~/aiwork/venv` | Python 가상환경 (`requirements.txt`) |
| `~/aiwork/results` | 결과 원본 (저장소에 올리지 않음) |
| `/mnt/ssd/kvcache/{raw,lz4}` | KV Cache 파일 (실험 중에만 생김) |
| `/mnt/ssd/swapfile` | swap 8G |
| `~/actions-runner` | GitHub Actions self-hosted runner (라벨 `self-hosted, Linux, X64`) |

## 2. llama.cpp와 모델

```sh
cd ~/aiwork
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp
git checkout 85cc432e2
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j8 --target llama-server
git rev-parse HEAD > ~/aiwork/llama_commit.txt
```

모델 (`~/aiwork/models`, 둘 다 Q4_K_M):

| 파일 | SHA256 |
| --- | --- |
| `qwen2.5-0.5b-instruct-q4_k_m.gguf` | `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db` |
| `Llama-3.2-1B-Instruct-Q4_K_M.gguf` | `6f85a640a97cf2bf5b8e764087b1e83da0fdb51d7c9fab7d0fece9385611df83` |

`cd ~/aiwork/models && sha256sum -c SHA256SUMS` 로 확인한다.

## 3. 실험 SSD와 swap

`/etc/fstab`:

```
UUID=<실험 SSD UUID> /mnt/ssd ext4 defaults,noatime,nofail 0 2
/mnt/ssd/swapfile none swap sw,nofail 0 0
```

```sh
sudo mkdir -p /mnt/ssd/kvcache/raw /mnt/ssd/kvcache/lz4 /mnt/ssd/scratch
sudo chown -R ondevice-ai: /mnt/ssd/kvcache /mnt/ssd/scratch
sudo fallocate -l 8G /mnt/ssd/swapfile && sudo chmod 600 /mnt/ssd/swapfile
sudo mkswap /mnt/ssd/swapfile && sudo swapon /mnt/ssd/swapfile
```

swap을 실험 SSD에 두었으므로 메모리 압박 실험(D4)에서는 swap I/O도 실험 SSD에서 일어난다.

## 4. CPU 클럭 고정 (부팅 시 적용)

`/etc/systemd/system/kvbench-tune.service`:

```ini
[Unit]
Description=KV bench CPU tuning
[Service]
Type=oneshot
ExecStart=/bin/sh -c 'for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > $g; done; echo 1 > /sys/devices/system/cpu/intel_pstate/no_turbo'
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
```

`sudo systemctl enable --now kvbench-tune` → 거버너 `performance`, 터보 끔, 최대 3600MHz.

## 5. 백그라운드 작업 끄기

측정 중 디스크·CPU를 쓰지 않도록 끈다.

```sh
sudo systemctl disable --now apt-daily.timer apt-daily-upgrade.timer fstrim.timer unattended-upgrades.service
```

## 6. 전용 sudo 명령

실험 스크립트는 아래 세 명령만 `sudo -n`으로 부른다. 모두 `root` 소유, `755`, `/usr/local/sbin/`.

| 명령 | 하는 일 |
| --- | --- |
| `kvb-drop-caches` | `sync` 후 `echo 3 > /proc/sys/vm/drop_caches` (cold 조건) |
| `kvb-io-limit <읽기> <쓰기>` / `reset` | 실험 SSD 장치에 `IOReadBandwidthMax`/`IOWriteBandwidthMax`를 `system.slice`, `user.slice`에 `--runtime`으로 설정 |
| `kvb-cpufreq <MHz>` / `reset` | 모든 코어 `scaling_max_freq` 설정 (cpuinfo 범위 안에서만) |

스크립트 원본은 공용 PC의 `/usr/local/sbin/kvb-*` 를 참고한다. sudoers (`sudo visudo -f /etc/sudoers.d/kvbench`):

```
ondevice-ai ALL=(root) NOPASSWD: /usr/local/sbin/kvb-drop-caches, /usr/local/sbin/kvb-io-limit, /usr/local/sbin/kvb-cpufreq
```

확인: `sudo -n -l` 에 위 세 명령이 NOPASSWD로 보여야 한다.

## 7. 메모리·CPU 사용률 제한 (systemd user scope)

`run_bench.py`는 `systemd-run --user --scope -p MemoryMax=...` 로 llama-server만 제한한다. 로그인하지 않은 상태(Actions runner)에서도 user 매니저가 떠 있도록 linger를 켠다.

```sh
sudo loginctl enable-linger ondevice-ai
XDG_RUNTIME_DIR=/run/user/$(id -u) systemd-run --user --scope --quiet true && echo ok
```

## 8. Python 환경과 도구

```sh
sudo apt install python3-venv fio sysstat      # sysstat = iostat
python3 -m venv ~/aiwork/venv
~/aiwork/venv/bin/pip install -r requirements.txt
```

## 9. 점검 목록

실험 전에 다음이 모두 맞는지 본다 (2차 실험 점검 결과는 `docs/results/phase2/env_check.md`).

- `git -C ~/aiwork/llama.cpp rev-parse --short=9 HEAD` → `85cc432e2`
- `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` → `performance`, `intel_pstate/no_turbo` → `1`
- `findmnt /mnt/ssd` → 실험 SSD, `swapon --show` → `/mnt/ssd/swapfile`
- `pgrep -a llama` 결과 없음, `/mnt/ssd/kvcache/{raw,lz4}` 비어 있음
