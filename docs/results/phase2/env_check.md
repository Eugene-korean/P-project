# 2차 실험 환경 점검 (단계 A)

점검 일시: 2026-11-10 · 점검 위치: 공용 PC (ondevice-ai)

## 하드웨어·OS

| 항목 | 값 |
| --- | --- |
| CPU | Intel Core i7-9700K, 8코어 8스레드 |
| 메모리 | 32GB (가용 약 29GiB) |
| OS / 커널 | Ubuntu 26.04.1 LTS / 7.0.0-38-generic |
| CPU 거버너 | `performance` |
| 터보 | 꺼짐 (`intel_pstate/no_turbo = 1`) |
| 최대 클럭 (scaling_max_freq) | 3600 MHz (cpuinfo 범위 800~3600 MHz) |

## llama.cpp·모델

| 항목 | 값 | 판정 |
| --- | --- | --- |
| 경로 | `~/aiwork/llama.cpp` | |
| 커밋 | `85cc432e2c8b92925f17dfb8937742541312f1d4` (`~/aiwork/llama_commit.txt`와 같음) | README의 `85cc432e2`와 일치 |
| 빌드 | `build/bin/llama-server` 있음 (공유 라이브러리 `libllama*.so` 링크) | 정상 |
| Qwen2.5-0.5B-Instruct Q4_K_M | `74a4da8c…7a9db` | `sha256sum -c` OK |
| Llama-3.2-1B-Instruct Q4_K_M | `6f85a640…11df83` | `sha256sum -c` OK |

## 공용 PC 메모리 현황 (`free -h`, 2026-11-10 실험 시작 전, llama-server 없음)

```
               total        used        free      shared  buff/cache   available
Mem:            30Gi       1.1Gi        28Gi        27Mi       820Mi        29Gi
Swap:          8.0Gi          0B       8.0Gi
```

| 항목 | 값 |
| --- | --- |
| 전체 | 31,182 MiB (30Gi) |
| OS·상주 프로세스 사용 (used) | 1,128 MiB. 큰 것: Claude Code 약 424 MiB, Actions Runner.Listener 약 128 MiB, fwupd·tailscaled 각 약 47 MiB |
| 페이지 캐시 (buff/cache) | 820 MiB |
| 사용 가능 (available) | 30,053 MiB (29Gi) |
| swap | 8.0Gi, 사용 0B |

→ 메모리 상한이 없는 조건(D1~D3, D5 b)에서는 두 모델(llama-server RSS 약 0.8~1.9GiB)이 메모리 부족 없이 돈다. 메모리 압박은 D4·D5(a)의 cgroup 상한으로만 만든다.

## 저장장치

| 항목 | 값 |
| --- | --- |
| OS SSD | `sda` WDC WDS250G2B0A (WD Blue 250GB), `/` 207G 남음 |
| 실험 SSD | `sdb` **Samsung SSD 840** (840 PRO 128GB), `/dev/sdb1` ext4 `rw,noatime` → `/mnt/ssd`, 103G 남음 |
| KV 경로 | `/mnt/ssd/kvcache/{raw,lz4}`, 둘 다 비어 있음 |
| swap | `/mnt/ssd/swapfile` **8G** (실험 SSD 위, 사용 0B). D4에서 swap I/O도 실험 SSD에서 발생함 |
| RAM 디스크 | `/dev/shm` tmpfs 16G |

### 실험 SSD 실측 속도 (fio 3.41, 1GB 파일, 1MiB 블록, 순차, 제한 없음)

| 측정 | 속도 |
| --- | --- |
| 순차 쓰기 (direct I/O) | 340.8 MB/s |
| 순차 읽기 (direct I/O) | 493.0 MB/s |
| 순차 읽기 (버퍼 I/O, `kvb-drop-caches` 직후 = cold 복원과 같은 경로) | 538.5 MB/s |

MB = 10^6 바이트. 측정 파일 `/mnt/ssd/scratch/fio_test.bin`은 측정 후 삭제함.

## 권한·제한 도구

| 항목 | 결과 |
| --- | --- |
| `/usr/local/sbin/kvb-io-limit` | 있음. `system.slice`·`user.slice`에 `IOReadBandwidthMax`/`IOWriteBandwidthMax` (runtime) 적용 |
| `/usr/local/sbin/kvb-cpufreq` | 있음. 모든 코어 `scaling_max_freq` 설정 |
| `/usr/local/sbin/kvb-drop-caches` | 있음. `sync` + `drop_caches=3` |
| `sudo -n` | 위 3개만 NOPASSWD로 허용됨 (`sudo -n -l` 확인) |
| `systemd-run --user --scope` | 동작함, linger = yes |

## Python 환경 (`~/aiwork/venv`)

| 항목 | 값 |
| --- | --- |
| Python | 3.14.4 |
| lz4 | 4.4.5 |
| matplotlib | 3.11.2 |
| numpy / pandas | 2.5.4 / 3.1.0 |
| pyyaml | 없음 (조건 파일은 JSON으로 하면 필요 없음) |
| fio | 3.41 (`/usr/bin/fio`) |
| iostat / vmstat | 있음 |
| 한글 폰트 | **없음** (`fc-list`도 없음, matplotlib에 CJK 폰트 없음) → venv pip으로 `koreanize-matplotlib`(NanumGothic 포함) 설치 예정 |

## 저장소·기타

| 항목 | 결과 |
| --- | --- |
| 작업 클론 | `~/aiwork/P-project` (새로 클론, 브랜치 `exp/phase2`, 기준 커밋 `ea2581a`). runner 폴더는 사용하지 않음 |
| 커밋 작성자 | 이 저장소에만 `Eugene-korean <341864668+Eugene-korean@users.noreply.github.com>` |
| `docs/SETUP.md` | **저장소에 없음** (`run_bench.py` 739행 오류 메시지에서 참조) |
| `gh` | 설치 안 됨 → push·PR은 사용자가 설치·로그인한 뒤 진행 |
| GitHub Actions runner | 서비스 실행 중 (`Runner.Listener`), 점검 시 작업(`Runner.Worker`) 없음 |
| 실행 중인 llama 프로세스 / 8080 포트 | 없음 / 비어 있음 |

## 1차 실험과 다른 점, 주의할 점

- 실험 SSD 제한 없는 실측 읽기 538 MB/s는 SATA 기준값(540MB/s)과 거의 같다 → D1이 "T4 PC(SATA SSD)" 등급 실측으로 쓰일 수 있다.
- swap 파일이 8G로 실험 SSD 위에 있다. D4의 `swap-max 1G`는 cgroup 허용량이라 문제없지만, swap 읽기·쓰기가 KV 파일 읽기와 같은 디스크를 쓴다.
- `kvb-io-limit`은 `system.slice`·`user.slice` 전체에 걸리므로 `--measure-disk`로 제한 적용 여부를 확인할 수 있다.
