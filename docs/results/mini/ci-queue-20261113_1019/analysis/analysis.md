# 2차 실험 분석 결과

생성: 2026-11-13 10:21 · 입력: `/home/ondevice-ai/aiwork/results/dev/ci-queue/mini/ci-queue-20261113_1019/sweep_summary.csv`

단위: 시간 ms, 속도 MB/s(10^6 바이트), 메모리 MiB, s 바이트/토큰, r 토큰/s. "계산값"은 측정값으로 식을 계산한 것, "실측"은 측정에서 직접 읽은 것.

## 토큰당 KV 크기 s

| model | s_bytes_per_token | header_bytes | lengths |
| --- | --- | --- | --- |
| qwen | 12304.0 | 628.0 | 3 |


## 조건별 r, T0, B*, N*

| stage | condition | model | cache | status | r_fit_tok_s | B_MB_s | T0_ms | T0_source | Bstar_MB_s(계산값) | Nstar_tok(계산값) | Nstar_tok(실측 교차) | speedup_4096 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | nolimit | qwen | cold | ok | 455.47 | 463.73 | 16.73 | 자기 조건 16토큰 | 5.6 | 7.7 | <16 (모든 길이에서 배율>1) |  |
| D2 | nolimit | qwen | cold | ok | 465.83 | 472.98 | 15.85 | 자기 조건 16토큰 | 5.73 | 7.5 | <16 (모든 길이에서 배율>1) |  |
| D2 | ramdisk | qwen | warm | ok | 466.3 | 9148.84 | 14.63 | 자기 조건 16토큰 | 5.74 | 6.8 | <16 (모든 길이에서 배율>1) |  |
| D2 | read20M | qwen | cold | ok | 469.25 | 19.97 | 15.85 | D2/nolimit (io.max 소파일 통과 보정) | 5.77 | 10.5 | <16 (모든 길이에서 배율>1) |  |
| D2 | read44M | qwen | cold | ok | 466.49 | 44.5 | 15.85 | D2/nolimit (io.max 소파일 통과 보정) | 5.74 | 8.5 | <16 (모든 길이에서 배율>1) |  |
| D2 | read5M | qwen | cold | ok | 510.32 | 5.0 | 15.85 | D2/nolimit (io.max 소파일 통과 보정) | 6.28 | ∞ | 141.7 |  |
| D3 | t4_f3600 | qwen | cold | ok | 249.7 | 284.72 | 16.44 | 자기 조건 16토큰 | 3.07 | 4.1 | <16 (모든 길이에서 배율>1) |  |
| D3 | t8_f1500 | qwen | cold | ok | 195.55 | 450.14 | 25.73 | 자기 조건 16토큰 | 2.41 | 5.1 | <16 (모든 길이에서 배율>1) |  |
| D3 | t8_f3600 | qwen | cold | ok | 465.94 | 452.76 | 15.69 | 자기 조건 16토큰 | 5.73 | 7.4 | <16 (모든 길이에서 배율>1) |  |
| D4 | mem1.5G | qwen | cold | ok |  | 482.28 |  |  |  |  | <1024 (모든 길이에서 배율>1) |  |
| D4 | mem2G | qwen | cold | ok |  | 353.49 |  |  |  |  | <1024 (모든 길이에서 배율>1) |  |
| D5 | rpi_like | qwen | cold | ok | 104.31 | 44.51 | 27.56 | 자기 조건 16토큰 | 1.28 | 3.0 | <16 (모든 길이에서 배율>1) |  |


## D2 손익분기식 검증 (B* 예측 vs 실측 교차)

| model | n_tokens | B_cross_MB_s(실측 보간) | Bstar_MB_s(계산값) | Bstar_T0_MB_s(계산값) | err_Bstar_% | err_Bstar_T0_% | speedup_by_B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| qwen | 16 | <5.0 (최저 B에서도 배율 2.08) | 4.71 | 7.6 |  |  | 5.0MB/s→x2.08; 20.0MB/s→x2.58; 44.5MB/s→x2.63; 473.0MB/s→x2.57 |
| qwen | 256 | 5.95 | 6.09 | 6.28 | 2.4 | 5.6 | 5.0MB/s→x0.82; 20.0MB/s→x4.0; 44.5MB/s→x23.67; 473.0MB/s→x22.4 |
| qwen | 1024 | <19.97 (최저 B에서도 배율 3.49) | 5.74 | 5.78 |  |  | 20.0MB/s→x3.49; 44.5MB/s→x9.38; 473.0MB/s→x53.4 |


## 메모리 (제한 없음): RSS 증가 vs 이론 KV 크기

| stage | condition | model | cache | n_tokens | rss_increase_MiB | kv_theory_MiB(계산값) |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | nolimit | qwen | cold | 16 | 48.4 | 0.2 |
| D1 | nolimit | qwen | cold | 256 | 49.0 | 3.0 |
| D1 | nolimit | qwen | cold | 1024 | 49.7 | 12.0 |
| D1 | nolimit | qwen | warm | 16 | 48.4 | 0.2 |
| D1 | nolimit | qwen | warm | 256 | 49.0 | 3.0 |
| D1 | nolimit | qwen | warm | 1024 | 49.7 | 12.0 |
| D2 | nolimit | qwen | cold | 16 | 48.4 | 0.2 |
| D2 | nolimit | qwen | cold | 256 | 49.0 | 3.0 |
| D2 | nolimit | qwen | cold | 1024 | 49.6 | 12.0 |
| D2 | ramdisk | qwen | warm | 16 | 48.4 | 0.2 |
| D2 | ramdisk | qwen | warm | 256 | 49.0 | 3.0 |
| D2 | ramdisk | qwen | warm | 1024 | 49.6 | 12.0 |
| D2 | read20M | qwen | cold | 16 | 48.4 | 0.2 |
| D2 | read20M | qwen | cold | 256 | 49.0 | 3.0 |
| D2 | read20M | qwen | cold | 1024 | 49.6 | 12.0 |
| D2 | read44M | qwen | cold | 16 | 48.5 | 0.2 |
| D2 | read44M | qwen | cold | 256 | 49.0 | 3.0 |
| D2 | read44M | qwen | cold | 1024 | 49.6 | 12.0 |
| D2 | read5M | qwen | cold | 16 | 30.5 | 0.2 |
| D2 | read5M | qwen | cold | 256 | 30.5 | 3.0 |
| D3 | t4_f3600 | qwen | cold | 16 | 47.0 | 0.2 |
| D3 | t4_f3600 | qwen | cold | 256 | 47.2 | 3.0 |
| D3 | t4_f3600 | qwen | cold | 1024 | 47.8 | 12.0 |
| D3 | t8_f1500 | qwen | cold | 16 | 48.4 | 0.2 |
| D3 | t8_f1500 | qwen | cold | 256 | 49.0 | 3.0 |
| D3 | t8_f1500 | qwen | cold | 1024 | 49.6 | 12.0 |
| D3 | t8_f3600 | qwen | cold | 16 | 48.4 | 0.2 |
| D3 | t8_f3600 | qwen | cold | 256 | 49.0 | 3.0 |
| D3 | t8_f3600 | qwen | cold | 1024 | 49.6 | 12.0 |
| D5 | rpi_like | qwen | cold | 16 | 47.0 | 0.2 |
| D5 | rpi_like | qwen | cold | 256 | 47.2 | 3.0 |
| D5 | rpi_like | qwen | cold | 1024 | 47.9 | 12.0 |
| D5 | rpi_like | qwen | warm | 16 | 47.0 | 0.2 |
| D5 | rpi_like | qwen | warm | 256 | 47.2 | 3.0 |
| D5 | rpi_like | qwen | warm | 1024 | 47.9 | 12.0 |


## D4 컨텍스트 크기별 대화 없을 때 메모리 (서버 시작 전 캐시 비움)

| model | mem_limit | ctx | kv_buffer_MiB | kv_theory_MiB(계산값) | compute_buffer_MiB | repack_buffer_MiB | rss_MiB | anon_MiB | file_MiB | swap_MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen | 1536M | 1024 | 12.0 | 12.0 | 38.27 | 28.05 | 576.2 | 95.4 | 480.8 | 0.0 |
| qwen | 없음 | 1024 | 12.0 | 12.0 | 38.27 | 28.05 | 576.1 | 95.4 | 480.7 | 0.0 |


## D4 메모리 압박

| model | mem_limit | status | n_tokens | runs | recompute_ms | resume_total_ms | speedup | swap_after_restore_MiB_max | vmstat_si_KiB | vmstat_so_KiB | all_match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen | 1536M | ok | 1024 | 1 | 2179.25 | 55.73 | 39.1 | 0.0 | 16 | 10 | True |
| qwen | 2G | ok | 1024 | 1 | 2180.83 | 41.0 | 53.19 | 0.0 | 16 | 10 | True |


## 저장 비용과 본전 재사용 횟수

| stage | condition | model | cache | n_tokens | save_total_ms | resume_total_ms | recompute_ms | breakeven_reuse |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | nolimit | qwen | cold | 16 | 14.92 | 17.15 | 41.32 | 1.327 |
| D1 | nolimit | qwen | cold | 256 | 17.43 | 24.4 | 516.13 | 0.085 |
| D1 | nolimit | qwen | cold | 1024 | 53.75 | 71.66 | 2238.93 | 0.058 |
| D2 | nolimit | qwen | cold | 16 | 6.59 | 16.27 | 41.77 | 0.896 |
| D2 | nolimit | qwen | cold | 256 | 16.44 | 23.1 | 517.37 | 0.08 |
| D2 | nolimit | qwen | cold | 1024 | 46.4 | 41.09 | 2193.87 | 0.041 |
| D2 | ramdisk | qwen | warm | 16 | 0.18 | 14.66 | 41.16 | 0.56 |
| D2 | ramdisk | qwen | warm | 256 | 1.04 | 15.04 | 535.92 | 0.031 |
| D2 | ramdisk | qwen | warm | 1024 | 3.8 | 18.37 | 2196.95 | 0.01 |
| D2 | read20M | qwen | cold | 16 | 23.96 | 16.06 | 41.44 | 1.577 |
| D2 | read20M | qwen | cold | 256 | 21.95 | 127.98 | 511.56 | 0.391 |
| D2 | read20M | qwen | cold | 1024 | 53.34 | 624.17 | 2177.25 | 0.436 |
| D2 | read44M | qwen | cold | 16 | 10.18 | 15.6 | 41.03 | 1.014 |
| D2 | read44M | qwen | cold | 256 | 23.39 | 21.74 | 514.45 | 0.092 |
| D2 | read44M | qwen | cold | 1024 | 45.74 | 233.39 | 2189.62 | 0.143 |
| D2 | read5M | qwen | cold | 16 | 11.23 | 19.65 | 40.93 | 1.452 |
| D2 | read5M | qwen | cold | 256 | 17.18 | 627.07 | 511.22 |  |
| D3 | t4_f3600 | qwen | cold | 16 | 6.07 | 17.13 | 71.44 | 0.427 |
| D3 | t4_f3600 | qwen | cold | 256 | 21.19 | 26.43 | 975.78 | 0.05 |
| D3 | t4_f3600 | qwen | cold | 1024 | 52.29 | 81.42 | 4091.34 | 0.033 |
| D3 | t8_f1500 | qwen | cold | 16 | 14.69 | 26.17 | 95.34 | 0.591 |
| D3 | t8_f1500 | qwen | cold | 256 | 21.18 | 33.67 | 1220.22 | 0.046 |
| D3 | t8_f1500 | qwen | cold | 1024 | 59.13 | 67.66 | 5219.56 | 0.025 |
| D3 | t8_f3600 | qwen | cold | 16 | 9.07 | 16.13 | 41.06 | 1.011 |
| D3 | t8_f3600 | qwen | cold | 256 | 26.45 | 27.91 | 510.57 | 0.113 |
| D3 | t8_f3600 | qwen | cold | 1024 | 47.58 | 67.53 | 2190.9 | 0.054 |
| D4 | mem1.5G | qwen | cold | 1024 | 66.28 | 55.73 | 2179.25 | 0.058 |
| D4 | mem2G | qwen | cold | 1024 | 48.29 | 41.0 | 2180.83 | 0.042 |
| D5 | rpi_like | qwen | cold | 16 | 6.73 | 32.0 | 165.57 | 0.29 |
| D5 | rpi_like | qwen | cold | 256 | 180.21 | 40.99 | 2328.76 | 0.097 |
| D5 | rpi_like | qwen | cold | 1024 | 666.02 | 250.05 | 9787.98 | 0.096 |


## 모델 비교 (Qwen vs Llama)

_(데이터 없음)_


## 기기별 판단 기준 (실측·예측 구분)

| device | model | kind | prefill_tok_s | read_MB_s | write_MB_s | Bstar_MB_s | T0_ms | Nstar_tok | recompute_4096_ms | load_4096_ms | save_4096_ms | speedup_4096 | criterion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 공용 PC (i7-9700K 8스레드 3.6GHz, SATA SSD) | qwen | 실측 | 455.47 | 463.73 |  | 5.6 | 16.73 | 7.7 |  |  |  |  | 측정한 모든 길이(16\~4,096토큰)에서 저장·로드가 이득 → 항상 저장 (계산 경계 N*≈7.7토큰, 읽기 5.6MB/s 이하로 느려지면 버리기) |
| 라즈베리파이 흉내 (4코어 1.5GHz, 읽기 44MB/s·쓰기 20MB/s) | qwen | 실측 | 104.31 | 44.51 |  | 1.28 | 27.56 | 3.0 |  |  |  |  | 측정한 모든 길이(16\~4,096토큰)에서 저장·로드가 이득 → 항상 저장 (계산 경계 N*≈3.0토큰, 읽기 1.28MB/s 이하로 느려지면 버리기) |
| Galaxy S25 (Snapdragon 8 Elite for Galaxy) | qwen | 공개 자료 없음 |  |  |  |  |  |  |  |  |  |  | Qwen2.5-0.5B의 Snapdragon 8 Elite for Galaxy Prefill 공개값을 찾지 못함 (지어내지 않음) |
| iPhone 16 Pro | qwen | 공개 자료 없음 |  |  |  |  |  |  |  |  |  |  | 이 모델의 iPhone 16 Pro Prefill 속도와 저장장치 읽기·쓰기 속도 공개 자료 없음 (지어내지 않음) |


Galaxy S25 예측 근거: Qualcomm AI Hub Llama-v3.2-1B-Instruct 모델 카드, 'Snapdragon 8 Elite For Galaxy Mobile', GENIE 런타임, 컨텍스트 4096: 4,096토큰 프롬프트 TTFT 1.01초(w4a16)\~2.03초(w4), 128토큰 이하 프롬프트(처리 1회) 0.03\~0.06초 (https://huggingface.co/qualcomm/Llama-v3.2-1B-Instruct)


출처: `/home/ondevice-ai/aiwork/results/dev/ci-queue/mini/ci-queue-20261113_1019` 아래 각 조건 폴더 (표의 result_dir 열은 `/home/ondevice-ai/aiwork/results/dev/ci-queue/mini/ci-queue-20261113_1019/analysis`의 CSV에 있음)
