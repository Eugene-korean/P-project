# 2차 실험 설계

## 목적

같은 질문에 답할 때 **(Prefill + 답변)** 시간과 **(저장장치에서 KV Cache 로드 + 답변)** 시간이
토큰 길이·CPU 성능·저장장치 성능에 따라 어떻게 달라지는지 실측해, 기기 등급별로
"KV Cache를 버리고 다시 계산하는 게 이득인 구간"과 "저장해 두고 로드하는 게 이득인 구간"의 경계를 찾는다.

검증할 손익분기식 (s = 토큰당 KV 크기 바이트, r = Prefill 처리 속도 토큰/s, B = 실제 읽기 속도, T0 = 기본 비용):

- 기본 비용을 무시하면 로드와 재계산이 같아지는 읽기 속도: **B\* = s × r**
- 기본 비용까지 넣은 경계 토큰 수: **N\* = T0 ÷ (1/r − s/B)**

1차 실험(2026-10-29, README "현재 결과")의 한계: 저장장치가 실제 기기보다 느렸고, 제한 없는 기준선이 없고,
손익분기점을 직접 관측하지 못했고, 메모리 사용량을 분석하지 않았다.

## 공통 설정

모델 Qwen 0.5B·Llama 1B 모두 (`--model both`), 저장 방식 RAW, 워밍업 2, 생성 토큰 32, cold 방법 drop,
반복 5회, 조건 시작마다 `--measure-disk`로 kv-dir 읽기·쓰기 속도 실측, llama-server `-lv 4`(KV 버퍼 크기 기록).

**처리 길이 최대 4,096토큰, 컨텍스트 `--ctx 4192` 모든 단계 고정** (llama.cpp가 256 배수로 올려 실제 n_ctx 4352, 6,000 이하).
실제 온디바이스 모델은 한 세션을 약 4,096토큰으로 제한하므로(애플 온디바이스 모델 기준) 그보다 긴 조건은 뺐다.
파일럿에서 측정한 8,192·16,384토큰 결과는 현실 범위 밖이라 보고서·저장소에 넣지 않고 공용 PC(`~/aiwork/results/phase2/pilot_long/`)에만 보관한다.

## 조건 (configs/phase2/)

| 단계 | 목적 | 조건 | 길이 | 캐시 |
| --- | --- | --- | --- | --- |
| D1 | 제한 없는 기준선 (PC 등급) | 제한 없음 | 16\~4096 (2배씩) | cold, warm |
| D2 | 로드 시간이 저장장치에만 좌우되는지, 손익분기점 관측 | io-read 5M·10M(B\* 근처, 길이 16·64·256만), 20M, 44M(microSD 수준), 100M, 제한 없음, RAM 디스크(`/dev/shm`, warm만). 쓰기·CPU 제한 없음 | 16, 64, 256, 1024, 4096 | cold |
| D3 | Prefill이 CPU에만 좌우되는지, B\*가 r에 비례하는지 | (a) 3600MHz + 스레드·코어 2, 4, 8 (b) 스레드·코어 8 + 1500, 2400, 3600MHz. `t8_f3600`이 (a)(b) 공통 | 16, 256, 1024, 4096 | cold |
| D4 | 토큰 수별 메모리, swap 발생 지점 | 제한 없음 RSS는 D1 재사용. `idle_ctx*`: --ctx 1024·2048·4096별 대화 없을 때 메모리·KV 버퍼 (제한 없음, 1.5G). mem-limit 4G, 3G, 2G, 1.5G (mem-high 75%, swap-max 1G). 모두 서버 시작 전 페이지 캐시 비움 | 1024, 4096 | cold |
| D5 | 1차 재현 + 라즈베리파이 흉내 | (a) 1차 조건 그대로 (b) 스레드·코어 4, 1500MHz, io-read 44M, io-write 20M | 16, 256, 1024, 4096 | cold, warm |

처음 계획에서 바꾼 것: 반복 10회 → 5회, D3의 스레드 1 제외, 길이 8,192·16,384 제외(최대 4,096), D2 5M·10M은 짧은 길이만.

D4에서 서버 시작 전 페이지 캐시를 비우는 이유: mmap한 모델 파일 페이지는 처음 읽은 cgroup에 메모리가 잡혀서,
캐시에 이미 있으면 서버의 메모리 상한에서 빠진다. 파일럿에서 같은 조건(Llama, 1.5G, ctx 2048)인데 캐시 상태에 따라 swap이 0\~65MiB로 달랐다.

## 실행 방법

공용 PC에서 (다른 실험이 없는지 확인한 뒤, 팀 공지 후):

```sh
cd ~/aiwork/P-project
PY=~/aiwork/venv/bin/python
$PY scripts/run_sweep.py configs/phase2/D1.json          # 단계 하나
$PY scripts/run_sweep.py configs/phase2/D2.json --only read44M,nolimit   # 조건 일부만
$PY scripts/run_sweep.py configs/phase2/D*.json --dry-run                # 실행할 명령만 보기
$PY scripts/run_sweep.py configs/phase2/D3.json --lengths 16,1024 --repeats 1 \
    --out-root ~/aiwork/results/phase2/pilot                             # 파일럿
$PY scripts/analyze_results.py                                           # 단계 E 계산
$PY scripts/plot_results.py                                              # 그래프
```

`run_sweep.py`가 하는 일:

- 조건을 시작하기 전마다 Actions 작업(`Runner.Worker`), llama 프로세스, 8080 포트를 확인하고 있으면 멈춘다
- `scripts/`, `configs/`에 커밋 안 된 변경이 있으면 시작하지 않는다 (결과의 `meta.json` `bench_repo_commit`으로 코드 버전을 추적하기 위해)
- 조건이 실패하면(서버 종료 등) `sweep_status.csv`에 기록하고 다음 조건으로 넘어간다. D4에서 메모리 부족으로 서버가 죽으면 `server_died`로 남는다
- 출력 불일치, io·클럭 제한 미적용, 조건 뒤 정리 실패(KV 파일·서버·제한이 남음)는 이상 징후로 보고 멈춘다
- 이미 결과가 있는 조건은 건너뛴다 (`--overwrite`로 다시 실행)

## 결과 위치

```
~/aiwork/results/phase2/
  env_check.md                 단계 A 환경 점검
  D1/<조건>/                   run_bench.py 결과 (results.csv, summary.csv, meta.json, vmstat.log, iostat.log, server_*.log, run.log)
  D1/sweep_status.csv          조건별 상태·소요 시간·이상 징후
  D1/sweep_summary.csv         조건 열을 붙여 합친 summary
  sweep_summary.csv            모든 단계를 합친 것 (분석·그래프 입력)
  analysis/                    analyze_results.py 결과 (CSV + analysis.md)
  plots/                       plot_results.py 결과 (PNG, fig1~fig9)
  REPORT.md                    최종 보고서
```

저장소에는 `docs/results/phase2/`에 보고서, 요약 CSV, 그래프만 복사해 올린다 (원본 결과 제외).

## 분석 정의 (scripts/analyze_results.py)

| 값 | 정의 |
| --- | --- |
| s | RAW 파일 크기를 길이에 대해 직선 맞춤한 기울기 (바이트/토큰) |
| r(N) | N ÷ 재계산 시간 (토큰/s) |
| r_fit | 1024토큰 이하에서 재계산 시간 = c0 + N/r_fit 직선 맞춤 (N\* 계산용) |
| B | 조건 시작 시 `--measure-disk` 실측 읽기 속도 (MB/s = 10^6 바이트/s) |
| T0 | 16토큰 복원 시간(이어서 시작까지) − 16토큰 파일 크기 ÷ B |
| B\* | s × r (계산값). T0까지 넣은 교차 속도 B\*_T0 = N·s ÷ (재계산(N) − T0)도 함께 |
| N\* | T0 ÷ (1/r_fit − s/B) (계산값). 실측 교차는 배율 = 1을 길이 축(로그)에서 보간 |
| 본전 재사용 횟수 | (저장 총시간 + 복원) ÷ (재계산 − 복원) |
| 메모리 증가 | 재계산 직후 RSS − 서버 시작 직후 RSS, 이론값 s × N과 비교 |

기기 등급: T1 저사양 보드(D5 b 실측), T4 PC SATA(D1 실측), 휴대폰 UFS 3.1(2,100MB/s)·UFS 4.0(4,200MB/s)·NVMe(7,450MB/s)는
D1의 r·T0에 해당 B를 넣은 계산값.
