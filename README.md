# KV Cache 저장·복원 벤치마크

같은 질문에 답할 때, LLM이 만든 중간 계산 결과(KV Cache)를 **처음부터 다시 계산하는 것**과 **저장장치에 저장해 뒀다가 불러오는 것** 중 무엇이 얼마나 빠른지 측정한다.

**지금 방향**: 모델과 프롬프트 길이는 평소엔 하나로 고정하고, **CPU(스레드·코어), 메모리(상한·swap), 저장장치(읽기 속도)** 를 바꿔 가며 응답 시간이 어떻게 달라지는지 본다. 같은 실험을 공용 PC에서 먼저 하고, 이후 Raspberry Pi에서 비교한다.

## 실험 환경 (공용 PC)

| 구분 | 내용 |
| --- | --- |
| CPU | Intel Core i7-9700K, 8코어 8스레드. 터보 끔, 3600MHz 고정 |
| 메모리 | 32GB DDR4 |
| OS SSD | WD Blue 250GB SATA. OS, llama.cpp, 모델, 결과 |
| 실험 SSD | Samsung 840 PRO 128GB SATA. KV Cache 파일과 swap만 |
| OS | Ubuntu Server 26.04.1 LTS |
| 추론 엔진 | llama.cpp 커밋 `85cc432e2` (CPU 빌드) |
| 모델 | Qwen2.5-0.5B-Instruct, Llama-3.2-1B-Instruct (GGUF Q4_K_M) |

구성 방법은 [`docs/SETUP.md`](docs/SETUP.md).

## 실험 실행

**본실험은 조건 파일(config)로만 돌린다.**

1. 조건 파일을 쓴다: `configs/<phase>/D1.json` — 작성법은 [`docs/CONFIG_GUIDE.md`](docs/CONFIG_GUIDE.md)
2. 단톡에 공지하고 `git pull` 후 main에 push한다
3. 공용 PC에서 자동으로 실험이 시작된다 (Actions → **kv-bench**에서 진행 상황 확인)

push하면 함께 일어나는 일:

| 작업 | 어디서 | 하는 일 |
| --- | --- | --- |
| kv-bench | 공용 PC | 새로 올라온 조건 파일만 차례로 실행 |
| conditions-doc | GitHub 서버 | 조건 파일을 표로 정리해 [`docs/conditions/`](docs/conditions/README.md)에 자동 커밋 |

conditions-doc이 main에 커밋하므로, **다음 push 전에 꼭 `git pull`** 한다.

### 버튼 실행

Actions → **kv-bench** → **Run workflow**.

- **조건 세트 다시 돌리기**: 맨 위 `config` 칸에 경로를 넣는다 (예: `configs/check` 폴더 전체, `configs/check/D1.json` 파일 하나). 이미 돌린 세트도 다시 돈다. 이때 아래 칸은 무시된다.
- **조건 하나만 돌리기**: `config` 칸을 비우고 아래 칸을 채운다.

| 칸 | 기본값 |
| --- | --- |
| config | 비움 |
| 모델 | qwen |
| 프롬프트 길이 | 16~4096 (9개) |
| 반복 횟수 | 5 |
| 스레드 수, 코어 개수 | 8 |
| 메모리 상한 | 없음 (넣으면 완만한 상한은 자동으로 75%) |
| swap 허용량 | 0 (메모리 상한을 걸 때만 의미 있음) |
| SSD 읽기 상한 | 없음 |

나머지(저장 방식 RAW·LZ4, cold, drop, 생성 32토큰, 워밍업 2)는 고정.

## 결과

- 실행 페이지 맨 아래 **Artifacts**에서 zip으로 받는다 (90일 보관)
- 공용 PC `~/aiwork/results/main/<phase>/<날짜_시각>/`에 영구 보관
- 결과 원본은 저장소에 커밋하지 않는다. 파일과 열의 뜻은 [`docs/README_phase2.md`](docs/README_phase2.md)의 "결과 파일"

## 사용 규칙

- 실험은 한 번에 하나씩 돈다. 돌리기 전에 단톡에 알린다.
- 실험 중에는 공용 PC에 SSH로 들어가 무거운 작업을 하지 않는다.
- push 전에 `git pull`. 테스트용 조건 파일은 확인이 끝나면 지운다.
- 공용 PC의 시스템 설정(CPU, swap, 타이머 등)을 바꾸면 이전 결과와 비교할 수 없게 된다. 바꾸기 전에 먼저 알린다.
- `.github/workflows/bench.yml`의 `uses:` 줄과 `runs-on:` 줄은 바꾸지 않는다.

## 저장소 구조

```
.github/workflows/bench.yml        실험 실행 (push 자동 실행 + 버튼)
.github/workflows/conditions.yml   조건 문서 자동 생성
configs/<phase>/                   조건 파일 (phase2 = 2차 실험)
scripts/run_bench.py               측정 스크립트 (조건 하나)
scripts/run_sweep.py               조건 파일 일괄 실행
scripts/list_configs.py            조건 파일 → docs/conditions/
scripts/analyze_results.py         2차 실험 분석
scripts/plot_results.py            2차 실험 그래프
prompts/corpus.txt                 프롬프트 재료
docs/CONFIG_GUIDE.md               조건 파일 작성법
docs/conditions/                   조건 목록 (자동 생성)
docs/SETUP.md                      공용 PC 구성
docs/EXPERIMENTS.md                2차 실험 설계
docs/README_phase2.md              1·2차 실험 당시 README (보관)
docs/results/                      1·2차 요약표·그래프·보고서
```

## 이전 기록

- 1·2차 실험 방법과 결과: [`docs/README_phase2.md`](docs/README_phase2.md)
- 2차 실험 보고서: [`docs/results/phase2/REPORT.md`](docs/results/phase2/REPORT.md)
