# 라즈베리파이 4 구성 및 실험 안내서 (재현용)

`scripts/run_bench.py`가 가정하는 환경을 라즈베리파이 4 Model B 단독(MicroSD 단일 스토리지) 환경에 맞게 구성한 안내서다.
새 라즈베리파이에서 같은 실험을 하려면 아래를 순서대로 맞춘다. **이미 구성된 기기에서는 다시 실행하지 않는다** (설정이 바뀌면 이전 결과와 비교할 수 없게 된다).

## 1. 장비와 경로

| 구분 | 값 |
| --- | --- |
| 기기 / CPU | Raspberry Pi 4 Model B / Broadcom BCM2711, Cortex-A72 (4코어 4스레드, ARM64) |
| 메모리 | 4GB |
| 통합 스토리지 | MicroSD 32GB (`/` 루트 파티션 및 `/mnt/ssd` 경로 통합 운영, ext4) |
| OS | Ubuntu Server 26.04.1 for RASPI LTS (64-bit, arm64), 사용자 `ondevice-ai` |

| 경로 | 내용 |
| --- | --- |
| `~/aiwork/llama.cpp` | llama.cpp, 커밋 `85cc432e2`, CPU 빌드 (`build/bin/llama-server`) |
| `~/aiwork/models` | GGUF 모델 2개와 `SHA256SUMS` |
| `~/aiwork/venv` | Python 가상환경 (`requirements.txt`, `lz4` 포함) |
| `~/aiwork/results` | 결과 원본 (저장소에 올리지 않음) |
| `/mnt/ssd/kvcache/{raw,lz4}` | KV Cache 파일 (실험 중에만 생김, MicroSD 루트 파티션 내 디렉터리) |
| `/mnt/ssd/swapfile` | swap 8G (MicroSD 루트 파티션 내 생성) |
| `~/actions-runner` | **(아직 구성 안 함)**<br> GitHub Actions self-hosted runner (라벨 `self-hosted, Linux, ARM64`) |

*일반 PC와의 차이점: 공용 PC는 Intel Core i7-9700K(x86_64, 8코어, 32GB RAM)에 OS용 SSD와 실험용 SATA SSD를 물리적으로 분리하여 사용하지만, 라즈베리파이 4는 ARM64 아키텍처(4코어)이며 추가 외장 SSD 없이 단일 MicroSD 카드 내부에 `/mnt/ssd` 디렉터리를 생성해 OS, Swap, KV Cache I/O를 모두 처리한다. 또한 GitHub Actions Runner 구성 시에도 `X64`가 아닌 `ARM64` 바이너리와 라벨을 사용한다.*

## 2. 부트 파라미터 설정 (cgroup 및 클럭 부스트 제어)

```sh
# 1. cgroup 메모리 컨트롤러 활성화 (기존 첫 줄 맨 끝에 줄바꿈 없이 추가)
sudo sed -i '1s/$/ cgroup_enable=cpuset cgroup_enable=memory cgroup_memory=1 swapaccount=1/' /boot/firmware/cmdline.txt

# 2. 펌웨어 부스트(1.8GHz) 비활성화 및 기본 최고 클럭(1.5GHz) 고정
echo "arm_boost=0" | sudo tee -a /boot/firmware/config.txt

# 3. 재부팅 후 적용 확인 (출력에 memory, io, cpu가 모두 있어야 함)
sudo reboot
cat /sys/fs/cgroup/cgroup.controllers
```

*일반 PC와의 차이점: 일반 x86_64 우분투 서버는 커널에서 메모리 cgroup 컨트롤러가 기본 활성화되어 있고 `/sys/devices/system/cpu/intel_pstate/no_turbo`를 통해 터보 부스트를 끈다. 반면 라즈베리파이용 우분투 커널은 메모리 cgroup이 기본적으로 꺼져 있어 `cmdline.txt`에 커널 파라미터를 직접 추가해야 `systemd-run`의 `MemoryMax` 제한이 작동하며, `intel_pstate` 드라이버가 없으므로 `/boot/firmware/config.txt`에 `arm_boost=0`을 넣어 클럭 부스트를 차단한다.*

## 3. llama.cpp와 모델

```sh
mkdir -p ~/aiwork/models ~/aiwork/results
cd ~/aiwork
git clone [https://github.com/ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) && cd llama.cpp
git checkout 85cc432e2
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j4 --target llama-server
git rev-parse HEAD > ~/aiwork/llama_commit.txt
```

모델 (`~/aiwork/models`, 둘 다 Q4_K_M):

| 파일 | SHA256 |
| --- | --- |
| `qwen2.5-0.5b-instruct-q4_k_m.gguf` | `74a4da8c9fdbcd15bd1f6d01d621410d31c6fc00986f5eb687824e7b93d7a9db` |
| `Llama-3.2-1B-Instruct-Q4_K_M.gguf` | `6f85a640a97cf2bf5b8e764087b1e83da0fdb51d7c9fab7d0fece9385611df83` |

`cd ~/aiwork/models && sha256sum -c SHA256SUMS` 로 확인한다.

*일반 PC와의 차이점: 공용 PC는 8코어와 32GB 메모리를 갖추고 있어 `cmake --build build -j8`로 빌드하지만, 라즈베리파이 4는 4코어 및 제한된 RAM 용량을 가지므로 컴파일 중 메모리 부족(OOM)과 과열을 방지하기 위해 `-j4`로 병렬 빌드 스레드 수를 낮춘다.*

## 4. 실험 스토리지 경로(`/mnt/ssd`)와 swap

`/etc/fstab`:

```
/mnt/ssd/swapfile none swap sw,nofail 0 0
```

```sh
# 기본 스왑(zram 또는 /swap.img) 비활성화 및 제거
sudo swapoff -a
sudo sed -i '/swap/d' /etc/fstab
sudo apt purge -y systemd-zram-generator zram-config 2>/dev/null || true

# MicroSD 루트 파일시스템 내부에 /mnt/ssd 경로 및 8GB 스왑 생성
sudo mkdir -p /mnt/ssd/kvcache/raw /mnt/ssd/kvcache/lz4 /mnt/ssd/scratch
sudo chown -R ondevice-ai: /mnt/ssd/kvcache /mnt/ssd/scratch
sudo fallocate -l 8G /mnt/ssd/swapfile && sudo chmod 600 /mnt/ssd/swapfile
sudo mkswap /mnt/ssd/swapfile && sudo swapon /mnt/ssd/swapfile
echo "/mnt/ssd/swapfile none swap sw,nofail 0 0" | sudo tee -a /etc/fstab
```

*일반 PC와의 차이점: 공용 PC는 별도의 물리 SSD(`UUID=<실험 SSD UUID>`)를 `/mnt/ssd`에 마운트하지만, 라즈베리파이는 추가 SSD 없이 단일 MicroSD 카드를 사용하므로 `/etc/fstab`에 디스크 마운트 항목을 넣지 않고 루트(`/`) 파티션 아래에 일반 디렉터리로 `/mnt/ssd`를 생성한다. 또한 `run_bench.py`는 `swapon --show`의 첫 번째 줄이 `/mnt/ssd`로 시작하는지 검사하므로, 라즈베리파이 우분투에 기본 활성화된 `zram`이나 기본 스왑을 반드시 제거해야 경고가 발생하지 않는다.*

## 5. CPU 클럭 고정 (부팅 시 적용)

`/etc/systemd/system/kvbench-tune.service`:

```ini
[Unit]
Description=KV bench CPU tuning (Raspberry Pi 4)
[Service]
Type=oneshot
ExecStart=/bin/sh -c 'for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do echo performance > $g; done'
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
```

`sudo systemctl enable --now kvbench-tune` → 거버너 `performance`, 최대 클럭 1500MHz(`arm_boost=0` 기준).

*일반 PC와의 차이점: 공용 PC의 서비스 파일에는 `echo 1 > /sys/devices/system/cpu/intel_pstate/no_turbo` 명령이 포함되어 있으나, ARM 아키텍처인 라즈베리파이 4에는 해당 경로가 존재하지 않아 실행 시 서비스가 실패(exit code 오류)하므로 이를 제거하고 `scaling_governor`만 `performance`로 고정한다.*

## 6. 백그라운드 작업 끄기

측정 중 디스크·CPU를 쓰지 않도록 끈다.

```sh
sudo systemctl disable --now apt-daily.timer apt-daily-upgrade.timer fstrim.timer unattended-upgrades.service
```

*일반 PC와의 차이점: 명령어는 공용 PC와 완전히 동일하다. 다만 단일 MicroSD에서 OS와 실험 I/O가 동시에 일어나므로 백그라운드 디스크 쓰기 차단이 실험 결과의 일관성에 훨씬 더 큰 영향을 미친다.*

## 7. 전용 sudo 명령

실험 스크립트는 아래 세 명령만 `sudo -n`으로 부른다. 모두 `root` 소유, `755`, `/usr/local/sbin/`.

| 명령 | 하는 일 |
| --- | --- |
| `kvb-drop-caches` | `sync` 후 `echo 3 > /proc/sys/vm/drop_caches` (cold 조건) |
| `kvb-io-limit <읽기> <쓰기>` / `reset` | `/mnt/ssd`가 속한 MicroSD 장치(`/dev/mmcblk0`)에 `IOReadBandwidthMax`/`IOWriteBandwidthMax`를 설정 (`-` 인자 허용) |
| `kvb-cpufreq <MHz>` / `reset` | 모든 코어 `scaling_max_freq` 설정 (600~1500MHz 범위 안에서만) |

```sh
# 1. kvb-drop-caches
sudo tee /usr/local/sbin/kvb-drop-caches << 'EOF'
#!/bin/sh
sync
echo 3 > /proc/sys/vm/drop_caches
EOF

# 2. kvb-io-limit (--target 옵션으로 MicroSD 루트 디바이스 탐색 및 '-' 인자 처리)
sudo tee /usr/local/sbin/kvb-io-limit << 'EOF'
#!/bin/bash
set -e
SRC=$(findmnt -n -o SOURCE --target /mnt/ssd)
PK=$(lsblk -no pkname "$SRC" | head -n1)
DISK="/dev/${PK:-$(basename "$SRC")}"

if [ "$1" = "reset" ]; then
    systemctl set-property --runtime system.slice IOReadBandwidthMax= IOWriteBandwidthMax=
    systemctl set-property --runtime user.slice IOReadBandwidthMax= IOWriteBandwidthMax=
    echo "io-limit reset ($DISK)"
    exit 0
fi

READ_LIM="$1"
WRITE_LIM="$2"
R_PROP=""
W_PROP=""
if [ -n "$READ_LIM" ] && [ "$READ_LIM" != "-" ]; then R_PROP="$DISK$READ_LIM"; fi
if [ -n "$WRITE_LIM" ] && [ "$WRITE_LIM" != "-" ]; then W_PROP="$DISK$WRITE_LIM"; fi

systemctl set-property --runtime system.slice IOReadBandwidthMax="$R_PROP" IOWriteBandwidthMax="$W_PROP"
systemctl set-property --runtime user.slice IOReadBandwidthMax="$R_PROP" IOWriteBandwidthMax="$W_PROP"
echo "io-limit applied on $DISK: read=${READ_LIM} write=${WRITE_LIM}"
EOF

# 3. kvb-cpufreq
sudo tee /usr/local/sbin/kvb-cpufreq << 'EOF'
#!/bin/bash
set -e
MIN_KHZ=$(cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_min_freq)
MAX_KHZ=$(cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq)

if [ "$1" = "reset" ]; then
    TARGET_KHZ=$MAX_KHZ
else
    TARGET_KHZ=$(( $1 * 1000 ))
    if [ "$TARGET_KHZ" -lt "$MIN_KHZ" ] || [ "$TARGET_KHZ" -gt "$MAX_KHZ" ]; then
        echo "Error: Frequency out of range (${MIN_KHZ} -${MAX_KHZ} kHz)" >&2
        exit 1
    fi
fi

for f in /sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq; do
    echo "$TARGET_KHZ" > "$f"
done
echo "cpufreq scaling_max_freq=${TARGET_KHZ}kHz"
EOF

sudo chmod 755 /usr/local/sbin/kvb-drop-caches /usr/local/sbin/kvb-io-limit /usr/local/sbin/kvb-cpufreq
echo "ondevice-ai ALL=(root) NOPASSWD: /usr/local/sbin/kvb-drop-caches, /usr/local/sbin/kvb-io-limit, /usr/local/sbin/kvb-cpufreq" | sudo tee /etc/sudoers.d/kvbench
sudo chmod 440 /etc/sudoers.d/kvbench
```

확인: `sudo -n -l` 에 위 세 명령이 NOPASSWD로 보여야 한다.

*일반 PC와의 차이점: 공용 PC에서는 `/mnt/ssd`가 독립된 마운트 포인트이므로 `findmnt /mnt/ssd`로 장치를 바로 찾을 수 있지만, 라즈베리파이에서는 일반 폴더이므로 `findmnt -n -o SOURCE --target /mnt/ssd`를 써서 상위 루트 파티션(`/dev/mmcblk0p2`)과 부모 블록 디바이스(`/dev/mmcblk0`)를 역추적해야 한다. 또한 CPU 클럭 조절 범위도 공용 PC(최대 3600MHz)와 달리 라즈베리파이 하드웨어 범위(600~1500MHz) 내에서만 동작한다.*

## 8. 메모리·CPU 사용률 제한 (systemd user scope)

`run_bench.py`는 `systemd-run --user --scope -p MemoryMax=...` 로 llama-server만 제한한다. 로그인하지 않은 상태에서도 user 매니저가 떠 있도록 linger를 켜고, 사용자 세션에 컨트롤러 권한을 위임(Delegate)한다.

```sh
sudo loginctl enable-linger ondevice-ai

sudo mkdir -p /etc/systemd/system/user@.service.d
sudo tee /etc/systemd/system/user@.service.d/delegate.conf << 'EOF'
[Service]
Delegate=cpu cpuset io memory pids
EOF

sudo systemctl daemon-reload
sudo systemctl restart user@$(id -u).service

# 확인: 메모리·스왑·CPU 제한이 모두 걸린 상태에서 ok가 출력되어야 함
XDG_RUNTIME_DIR=/run/user/$(id -u) systemd-run --user --scope -p MemoryMax=512M -p MemorySwapMax=0 -p CPUQuota=100% --quiet true && echo ok
```

*일반 PC와의 차이점: 공용 PC에서는 `loginctl enable-linger`만으로도 동작할 수 있으나, 라즈베리파이 우분투 환경에서는 `user@.service`에 `Delegate=cpu cpuset io memory pids` 설정을 명시적으로 추가해야 일반 사용자(`--user`) scope에서 `MemoryMax`와 `MemorySwapMax` 속성을 거부당하지 않고 사용할 수 있다.*

## 9. Python 환경과 도구

```sh
sudo apt update
sudo apt install -y build-essential cmake git python3-venv python3-pip fio sysstat bc tmux jq curl lz4
python3 -m venv ~/aiwork/venv
~/aiwork/venv/bin/pip install -r requirements.txt
~/aiwork/venv/bin/pip install lz4
```

*일반 PC와의 차이점: `run_bench.py`가 내부적으로 사용하는 `lz4.frame` 파이썬 모듈뿐만 아니라, 아래 수동 실험에서 터미널 명령어로 직접 호출하는 `tmux`, `jq`, `curl`, `lz4` CLI 패키지를 함께 설치해야 수동·자동 실험이 모두 오류 없이 작동한다.*

## 10. 점검 목록

실험 전에 다음이 모두 맞는지 본다.

- `git -C ~/aiwork/llama.cpp rev-parse --short=9 HEAD` → `85cc432e2`
- `cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` → `performance`
- `findmnt --target /mnt/ssd` → `/dev/mmcblk0p2`, `swapon --show` → `/mnt/ssd/swapfile` (단독 1개만 표시)
- `pgrep -a llama` 결과 없음, `/mnt/ssd/kvcache/{raw,lz4}` 비어 있음

*일반 PC와의 차이점: 라즈베리파이에는 `intel_pstate/no_turbo` 파일이 없으므로 점검 항목에서 제외하고, `/mnt/ssd`가 별도 마운트가 아니므로 `findmnt /mnt/ssd` 대신 `findmnt --target /mnt/ssd`로 확인한다.*

---

## 11. 수동 실험 방법 (터미널 직접 실행)

자동화 스크립트(`run_bench.py`)를 돌리기 전, 터미널에서 직접 명령어를 입력해 KV Cache의 **재계산(Prefill) vs RAW 저장·복원 vs LZ4 압축 저장·복원** 시간을 측정하고 생성 결과가 완벽히 일치하는지 검증하는 절차다.

*일반 PC 수동 실험 안내서와의 차이점:*
- *스레드 수(`-t`) 조정: 공용 PC 안내서는 8코어 기준인 `-t 8`을 사용하지만, 4코어인 라즈베리파이 4에서 `-t 8`을 주면 컨텍스트 스위칭 오버헤드로 인해 처리 속도가 크게 저하되므로 `-t 4`로 변경했다.*
- *프롬프트 연산 대기 시간 및 토큰 길이(`N`): 공용 PC에서는 `N=2048` 재계산이 수 초 내에 끝나지만, 라즈베리파이 4(Cortex-A72)는 초당 약 15~25토큰을 처리하므로 `N=2048` 실행 시 `curl -s` 상태에서 약 1분 30초~3분간 화면 출력이 멈춘 것처럼 대기하게 된다. 빠른 동작 확인을 위해 `N=128`로 먼저 테스트한 뒤 본 실험 길이(`2048` 등)로 늘리는 방식을 권장한다.*
- *출력 비교(`diff`) 정합성 보정: 기존 안내서처럼 2번(재계산) 단계에서 바로 32토큰을 생성해 버리면 슬롯에 `N+32`개의 토큰이 남고, 전체 프롬프트 일괄 연산과 복원 후 단일 토큰 연산 간의 부동소수점 배치 차이로 인해 4번 복원 출력과 `diff` 불일치가 발생할 수 있다. 따라서 `run_bench.py`의 원리와 동일하게 **① `n_predict: 1`로 재계산 시간을 측정 → ② 슬롯 저장 → ③ 저장 직후 상태에서 32토큰 기준 출력(`A.json`) 생성** 순서로 분리하여 복원 결과(`B.json`, `C.json`)와 비트 단위로 100% 일치하도록 수정했다.*
- *명령어 호출 경로 및 헤더 명시: 우분투 `sudoers` 보안 정책에 맞춰 `sudo -n kvb-drop-caches`를 전체 경로(`sudo -n /usr/local/sbin/kvb-drop-caches`)로 수정하고, 최신 `llama-server`에서 오류가 나지 않도록 `curl` 요청에 `-H "Content-Type: application/json"` 헤더와 LZ4 복원 후 검증 단계를 보완했다.*

### (0) 준비 (최초 1회)

먼저 `tmux` 세션을 열고 백그라운드에서 `llama-server`를 실행한다. 라즈베리파이의 4코어에 맞춰 `-t 4` 옵션을 사용한다.

```bash
tmux new -s exp
cd ~/aiwork/llama.cpp
./build/bin/llama-server -m ~/aiwork/models/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  -t 4 -c 8192 -np 1 --slot-save-path /mnt/ssd/kvcache/raw/ --port 8080
```

화면에 `server is listening` 로그가 나타나면 `Ctrl+b`를 누른 뒤 손을 떼고 `d`를 눌러 `tmux` 세션에서 빠져나온다. (나중에 다른 모델로 바꾸려면 `tmux attach -t exp`로 들어가서 서버를 끄고 `-m` 경로만 바꿔 다시 켜면 된다.)

다음으로 프롬프트 재료를 준비한다. 동일한 문장을 반복하면 LZ4 압축률이 비정상적으로 높게 왜곡되므로, 실제 문서 파일들을 이어 붙여 토큰화한다.

```bash
cat ~/aiwork/llama.cpp/docs/*.md ~/aiwork/llama.cpp/README.md > /tmp/corpus.txt
jq -n --rawfile c /tmp/corpus.txt '{content:$c}' \
  | curl -s -H "Content-Type: application/json" localhost:8080/tokenize -d @- \
  | jq '.tokens' > /tmp/tokens.json
jq length /tmp/tokens.json   # 전체 토큰 수 확인 (8,000 이상이면 충분)
```

### (1) 토큰 길이(`N`) 지정 및 요청 파일 생성

원하는 프롬프트 토큰 길이 `N`을 설정하고 두 종류의 요청 파일을 만든다.
- `req_prefill.json` (`n_predict: 1`): 순수하게 프롬프트 `N`개를 읽어들여 KV Cache를 만드는 재계산 시간 측정용이다.
- `req.json` (`n_predict: 32`): KV Cache 저장 직후 및 복원 직후에 이어서 32개의 토큰을 생성해 출력이 같은지 비교하는 용도다.

*(참고: 라즈베리파이에서 처음 명령어가 잘 도는지 빠르게 확인하려면 `N=128`로 먼저 실행해 보고, 본 측정에서 `512`, `1024`, `2048`, `4096` 등으로 바꿔가며 반복한다.)*

```bash
N=128   # 동작 확인 후 2048 등으로 변경
jq --argjson n $N '{prompt: .[:$n], n_predict:1, temperature:0, cache_prompt:true, id_slot:0}' \
  /tmp/tokens.json > /tmp/req_prefill.json

jq --argjson n $N '{prompt: .[:$n], n_predict:32, temperature:0, cache_prompt:true, id_slot:0}' \
  /tmp/tokens.json > /tmp/req.json
```

### (2) 재계산 (기준 시간 측정)

슬롯의 기존 캐시를 깨끗이 지운(`erase`) 다음, 프롬프트 `N`개를 처음부터 전부 계산하게 한다. (`N=2048` 기준 약 1분 30초~3분 소요)

```bash
curl -s -X POST "localhost:8080/slots/0?action=erase" > /dev/null
time curl -s -H "Content-Type: application/json" localhost:8080/completion -d @/tmp/req_prefill.json \
  | jq '{prompt_n: .timings.prompt_n, prompt_ms: .timings.prompt_ms}'
```

여기서 출력된 `prompt_ms`가 **재계산 시간(Prefill 시간)**이다.

### (3) RAW 저장 및 기준 출력(`A.json`) 생성

방금 계산된 슬롯의 KV Cache를 MicroSD(`/mnt/ssd/kvcache/raw/`)에 파일로 저장하고 `sync`를 호출해 실제 스토리지 플래시 메모리까지 쓰기를 완료한다. 그 직후, 동일한 KV 상태에서 32토큰을 생성해 기준 출력 파일(`A.json`)로 보관한다.

```bash
# 1) KV Cache를 RAW 파일로 저장
curl -s -X POST "localhost:8080/slots/0?action=save" \
  -H "Content-Type: application/json" \
  -d "{\"filename\":\"kv_$N.bin\"}" | jq '{n_written: .n_written, save_ms: .timings.save_ms}'
time sync

# 2) 저장 직후의 KV 상태에서 32토큰 기준 출력(A.json) 생성
curl -s -H "Content-Type: application/json" localhost:8080/completion -d @/tmp/req.json > /tmp/A.json
```

- **실제 RAW 저장 시간** = `save_ms` + `time sync`의 `real` 시간이다 (`save_ms`만으로는 OS 페이지 캐시에 넘긴 시간만 측정된다).

### (4) RAW 복원 (cold / warm)

슬롯을 비우고 OS 페이지 캐시까지 비운 뒤(`cold` 조건), 저장해 둔 RAW KV 파일을 불러와 동일한 32토큰 생성 요청을 보낸다. 이미 KV Cache가 복원되었으므로 프롬프트 전체를 다시 계산하지 않고 마지막 토큰 1개(`prompt_n: 1`)만 처리하며 즉시 생성이 시작된다.

```bash
curl -s -X POST "localhost:8080/slots/0?action=erase" > /dev/null
sudo -n /usr/local/sbin/kvb-drop-caches

# 1) 스토리지에서 슬롯으로 KV Cache 복원
curl -s -X POST "localhost:8080/slots/0?action=restore" \
  -H "Content-Type: application/json" \
  -d "{\"filename\":\"kv_$N.bin\"}" | jq '{restore_ms: .timings.restore_ms}'

# 2) 복원된 상태에서 동일 요청 실행 및 출력(B.json) 비교
curl -s -H "Content-Type: application/json" localhost:8080/completion -d @/tmp/req.json | tee /tmp/B.json \
  | jq '{prompt_n: .timings.prompt_n, prompt_ms: .timings.prompt_ms}'

diff <(jq -r .content /tmp/A.json) <(jq -r .content /tmp/B.json) && echo "출력 동일"
```

- **RAW 복원 총 시간** = `restore_ms` + 두 번째 요청의 `prompt_ms`이다.
- `prompt_n`이 `1`로 나오고 `"출력 동일"`이 찍히면 정상이다.
- **warm 조건**을 측정하려면 위 명령에서 `sudo -n /usr/local/sbin/kvb-drop-caches` 줄만 제외하고 똑같이 실행하면 된다.

### (5) LZ4 압축 저장 및 복원

저장된 RAW 파일을 LZ4로 압축하여 용량 감소율과 압축·해제 시간을 측정한다. 복원 시에는 압축을 푼 뒤 슬롯에 복원하고 동일하게 출력(`C.json`)이 일치하는지 확인한다.

```bash
cd /mnt/ssd/kvcache
time sh -c "lz4 -q -f raw/kv_$N.bin lz4/kv_$N.bin.lz4 && sync"   # 압축 + sync 시간 측정
ls -lh raw/kv_$N.bin lz4/kv_$N.bin.lz4                           # 파일 크기 및 압축률 확인
rm raw/kv_$N.bin

# cold 상태에서 압축 해제 후 복원
curl -s -X POST "localhost:8080/slots/0?action=erase" > /dev/null
sudo -n /usr/local/sbin/kvb-drop-caches

time lz4 -q -d -f lz4/kv_$N.bin.lz4 raw/kv_$N.bin                # 압축 해제 시간 측정
curl -s -X POST "localhost:8080/slots/0?action=restore" \
  -H "Content-Type: application/json" \
  -d "{\"filename\":\"kv_$N.bin\"}" | jq '{restore_ms: .timings.restore_ms}'

curl -s -H "Content-Type: application/json" localhost:8080/completion -d @/tmp/req.json | tee /tmp/C.json \
  | jq '{prompt_n: .timings.prompt_n, prompt_ms: .timings.prompt_ms}'

diff <(jq -r .content /tmp/A.json) <(jq -r .content /tmp/C.json) && echo "출력 동일"
```

- **LZ4 복원 총 시간** = `압축 해제 시간(real)` + `restore_ms` + `prompt_ms`이다.

### (6) 기록 및 실험 종료 후 정리

각 조건(모델, 토큰 길이 `N`, cold/warm)마다 **재계산 ms, 저장 ms(+sync), RAW/LZ4 파일 크기, 복원 ms, 압축·해제 ms, 출력 동일 여부**를 기록한다.

실험이 끝나면 다음 실험에 영향을 주지 않도록 캐시 파일과 백그라운드 서버를 정리한다.

```bash
rm -f /mnt/ssd/kvcache/raw/* /mnt/ssd/kvcache/lz4/* /tmp/A.json /tmp/B.json /tmp/C.json
tmux attach -t exp   # 접속 후 Ctrl+C로 llama-server 종료, 이어서 exit 입력
pgrep -a llama || echo "정리 완료"
```
