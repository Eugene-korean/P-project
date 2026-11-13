# mini 분석 결과 (ci-queue-20261113_1610)

생성: 2026-11-13 16:13 · 입력: `/home/ondevice-ai/aiwork/results/dev/ci-queue/mini/ci-queue-20261113_1610/sweep_summary.csv`

단위: 시간 ms, 속도 MB/s(10^6 바이트), 메모리 MiB, s 바이트/토큰, r 토큰/s. "계산값"은 측정값으로 식을 계산한 것, "실측"은 측정에서 직접 읽은 것.

## 토큰당 KV 크기 s

| model | s_bytes_per_token | header_bytes | lengths |
| --- | --- | --- | --- |
| qwen | 12304.0 | 628.0 | 3 |


## 조건별 r, T0, B*, N*

| stage | condition | model | cache | status | r_fit_tok_s | B_MB_s | T0_ms | T0_source | Bstar_MB_s(계산값) | Nstar_tok(계산값) | Nstar_tok(실측 교차) | speedup_4096 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | nolimit | qwen | cold | ok | 465.44 | 371.62 | 14.92 | 자기 조건 16토큰 | 5.73 | 7.1 | <16 (모든 길이에서 배율>1) |  |
| D2 | nolimit | qwen | cold | ok | 466.46 | 494.34 | 17.29 | 자기 조건 16토큰 | 5.74 | 8.2 | <16 (모든 길이에서 배율>1) |  |
| D2 | ramdisk | qwen | warm | ok | 463.67 | 9091.26 | 13.63 | 자기 조건 16토큰 | 5.71 | 6.3 | <16 (모든 길이에서 배율>1) |  |
| D2 | read20M | qwen | cold | ok | 469.44 | 19.97 | 17.29 | D2/nolimit (io.max 소파일 통과 보정) | 5.78 | 11.4 | <16 (모든 길이에서 배율>1) |  |
| D2 | read44M | qwen | cold | ok | 465.66 | 44.53 | 17.29 | D2/nolimit (io.max 소파일 통과 보정) | 5.73 | 9.2 | <16 (모든 길이에서 배율>1) |  |
| D2 | read5M | qwen | cold | ok | 520.83 | 4.99 | 17.29 | D2/nolimit (io.max 소파일 통과 보정) | 6.41 | ∞ | 171.7 |  |
| D3 | t4_f3600 | qwen | cold | ok | 249.91 | 305.55 | 16.17 | 자기 조건 16토큰 | 3.07 | 4.1 | <16 (모든 길이에서 배율>1) |  |
| D3 | t8_f1500 | qwen | cold | ok | 196.72 | 534.77 | 26.99 | 자기 조건 16토큰 | 2.42 | 5.3 | <16 (모든 길이에서 배율>1) |  |
| D3 | t8_f3600 | qwen | cold | ok | 468.18 | 474.76 | 14.94 | 자기 조건 16토큰 | 5.76 | 7.1 | <16 (모든 길이에서 배율>1) |  |
| D4 | mem1.5G | qwen | cold | ok |  | 383.73 |  |  |  |  | <1024 (모든 길이에서 배율>1) |  |
| D4 | mem2G | qwen | cold | ok |  | 314.41 |  |  |  |  | <1024 (모든 길이에서 배율>1) |  |
| D5 | rpi_like | qwen | cold | ok | 104.28 | 44.53 | 28.12 | 자기 조건 16토큰 | 1.28 | 3.0 | <16 (모든 길이에서 배율>1) |  |


## D2 손익분기식 검증 (B* 예측 vs 실측 교차)

| model | n_tokens | B_cross_MB_s(실측 보간) | Bstar_MB_s(계산값) | Bstar_T0_MB_s(계산값) | err_Bstar_% | err_Bstar_T0_% | speedup_by_B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| qwen | 16 | <4.99 (최저 B에서도 배율 3.25) | 4.8 | 8.3 |  |  | 5.0MB/s→x3.25; 20.0MB/s→x2.73; 44.5MB/s→x2.74; 494.3MB/s→x2.32 |
| qwen | 256 | 5.92 | 6.07 | 6.28 | 2.6 | 6.1 | 5.0MB/s→x0.82; 20.0MB/s→x4.11; 44.5MB/s→x23.64; 494.3MB/s→x22.82 |
| qwen | 1024 | <19.97 (최저 B에서도 배율 3.47) | 5.75 | 5.8 |  |  | 20.0MB/s→x3.47; 44.5MB/s→x9.41; 494.3MB/s→x51.51 |


## 메모리 (제한 없음): RSS 증가 vs 이론 KV 크기

| stage | condition | model | cache | n_tokens | rss_increase_MiB | kv_theory_MiB(계산값) |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | nolimit | qwen | cold | 16 | 48.5 | 0.2 |
| D1 | nolimit | qwen | cold | 256 | 49.1 | 3.0 |
| D1 | nolimit | qwen | cold | 1024 | 49.7 | 12.0 |
| D1 | nolimit | qwen | warm | 16 | 48.5 | 0.2 |
| D1 | nolimit | qwen | warm | 256 | 49.1 | 3.0 |
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
| D2 | read44M | qwen | cold | 256 | 49.1 | 3.0 |
| D2 | read44M | qwen | cold | 1024 | 49.7 | 12.0 |
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
| D3 | t8_f3600 | qwen | cold | 1024 | 49.5 | 12.0 |
| D5 | rpi_like | qwen | cold | 16 | 46.9 | 0.2 |
| D5 | rpi_like | qwen | cold | 256 | 47.2 | 3.0 |
| D5 | rpi_like | qwen | cold | 1024 | 47.8 | 12.0 |
| D5 | rpi_like | qwen | warm | 16 | 46.9 | 0.2 |
| D5 | rpi_like | qwen | warm | 256 | 47.2 | 3.0 |
| D5 | rpi_like | qwen | warm | 1024 | 47.8 | 12.0 |


## D4 컨텍스트 크기별 대화 없을 때 메모리 (서버 시작 전 캐시 비움)

| model | mem_limit | ctx | kv_buffer_MiB | kv_theory_MiB(계산값) | compute_buffer_MiB | repack_buffer_MiB | rss_MiB | anon_MiB | file_MiB | swap_MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen | 1536M | 1024 | 12.0 | 12.0 | 38.27 | 28.05 | 576.2 | 95.4 | 480.8 | 0.0 |
| qwen | 없음 | 1024 | 12.0 | 12.0 | 38.27 | 28.05 | 576.1 | 95.4 | 480.7 | 0.0 |


## D4 메모리 압박

| model | mem_limit | status | n_tokens | runs | recompute_ms | resume_total_ms | speedup | swap_after_restore_MiB_max | vmstat_si_KiB | vmstat_so_KiB | all_match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen | 1536M | ok | 1024 | 1 | 2175.18 | 72.03 | 30.2 | 0.0 | 16 | 10 | True |
| qwen | 2G | ok | 1024 | 1 | 2174.29 | 48.04 | 45.26 | 0.0 | 16 | 10 | True |


## 저장 비용과 본전 재사용 횟수

| stage | condition | model | cache | n_tokens | save_total_ms | resume_total_ms | recompute_ms | breakeven_reuse |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | nolimit | qwen | cold | 16 | 10.88 | 15.46 | 40.97 | 1.032 |
| D1 | nolimit | qwen | cold | 256 | 23.41 | 22.03 | 517.88 | 0.092 |
| D1 | nolimit | qwen | cold | 1024 | 61.65 | 49.38 | 2195.13 | 0.052 |
| D2 | nolimit | qwen | cold | 16 | 5.68 | 17.69 | 41.01 | 1.003 |
| D2 | nolimit | qwen | cold | 256 | 15.97 | 22.74 | 518.93 | 0.078 |
| D2 | nolimit | qwen | cold | 1024 | 50.46 | 42.53 | 2191.08 | 0.043 |
| D2 | ramdisk | qwen | warm | 16 | 0.18 | 13.66 | 41.11 | 0.504 |
| D2 | ramdisk | qwen | warm | 256 | 1.02 | 14.96 | 513.15 | 0.032 |
| D2 | ramdisk | qwen | warm | 1024 | 3.96 | 18.43 | 2201.51 | 0.01 |
| D2 | read20M | qwen | cold | 16 | 6.52 | 15.32 | 41.88 | 0.822 |
| D2 | read20M | qwen | cold | 256 | 20.67 | 128.39 | 527.79 | 0.373 |
| D2 | read20M | qwen | cold | 1024 | 51.56 | 627.79 | 2181.58 | 0.437 |
| D2 | read44M | qwen | cold | 16 | 5.95 | 15.01 | 41.12 | 0.803 |
| D2 | read44M | qwen | cold | 256 | 24.34 | 21.94 | 518.58 | 0.093 |
| D2 | read44M | qwen | cold | 1024 | 48.15 | 233.24 | 2194.52 | 0.143 |
| D2 | read5M | qwen | cold | 16 | 9.03 | 17.68 | 57.54 | 0.67 |
| D2 | read5M | qwen | cold | 256 | 20.45 | 629.21 | 518.35 |  |
| D3 | t4_f3600 | qwen | cold | 16 | 11.92 | 16.81 | 71.45 | 0.526 |
| D3 | t4_f3600 | qwen | cold | 256 | 27.41 | 47.03 | 974.1 | 0.08 |
| D3 | t4_f3600 | qwen | cold | 1024 | 47.49 | 56.58 | 4087.82 | 0.026 |
| D3 | t8_f1500 | qwen | cold | 16 | 17.67 | 27.36 | 95.28 | 0.663 |
| D3 | t8_f1500 | qwen | cold | 256 | 22.3 | 42.72 | 1218.04 | 0.055 |
| D3 | t8_f1500 | qwen | cold | 1024 | 67.02 | 94.51 | 5190.34 | 0.032 |
| D3 | t8_f3600 | qwen | cold | 16 | 7.08 | 15.36 | 41.33 | 0.864 |
| D3 | t8_f3600 | qwen | cold | 256 | 21.62 | 25.5 | 516.55 | 0.096 |
| D3 | t8_f3600 | qwen | cold | 1024 | 47.72 | 41.57 | 2183.22 | 0.042 |
| D4 | mem1.5G | qwen | cold | 1024 | 57.92 | 72.03 | 2175.18 | 0.062 |
| D4 | mem2G | qwen | cold | 1024 | 52.14 | 48.04 | 2174.29 | 0.047 |
| D5 | rpi_like | qwen | cold | 16 | 6.65 | 32.56 | 165.16 | 0.296 |
| D5 | rpi_like | qwen | cold | 256 | 185.09 | 40.82 | 2333.88 | 0.099 |
| D5 | rpi_like | qwen | cold | 1024 | 670.15 | 253.41 | 9792.19 | 0.097 |


## 모델 비교 (Qwen vs Llama)

_(데이터 없음)_


## 기기별 판단 기준 (실측·예측 구분)

| device | model | kind | prefill_tok_s | read_MB_s | write_MB_s | Bstar_MB_s | T0_ms | Nstar_tok | recompute_4096_ms | load_4096_ms | save_4096_ms | speedup_4096 | criterion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 공용 PC (i7-9700K 8스레드 3.6GHz, SATA SSD) | qwen | 실측 | 465.44 | 371.62 |  | 5.73 | 14.92 | 7.1 |  |  |  |  | 측정한 모든 길이(16\~4,096토큰)에서 저장·로드가 이득 → 항상 저장 (계산 경계 N*≈7.1토큰, 읽기 5.73MB/s 이하로 느려지면 버리기) |
| 라즈베리파이 흉내 (4코어 1.5GHz, 읽기 44MB/s·쓰기 20MB/s) | qwen | 실측 | 104.28 | 44.53 |  | 1.28 | 28.12 | 3.0 |  |  |  |  | 측정한 모든 길이(16\~4,096토큰)에서 저장·로드가 이득 → 항상 저장 (계산 경계 N*≈3.0토큰, 읽기 1.28MB/s 이하로 느려지면 버리기) |
| Galaxy S25 (Snapdragon 8 Elite for Galaxy) | qwen | 공개 자료 없음 |  |  |  |  |  |  |  |  |  |  | Qwen2.5-0.5B의 Snapdragon 8 Elite for Galaxy Prefill 공개값을 찾지 못함 (지어내지 않음) |
| iPhone 16 Pro | qwen | 공개 자료 없음 |  |  |  |  |  |  |  |  |  |  | 이 모델의 iPhone 16 Pro Prefill 속도와 저장장치 읽기·쓰기 속도 공개 자료 없음 (지어내지 않음) |


Galaxy S25 예측 근거: Qualcomm AI Hub Llama-v3.2-1B-Instruct 모델 카드, 'Snapdragon 8 Elite For Galaxy Mobile', GENIE 런타임, 컨텍스트 4096: 4,096토큰 프롬프트 TTFT 1.01초(w4a16)\~2.03초(w4), 128토큰 이하 프롬프트(처리 1회) 0.03\~0.06초 (https://huggingface.co/qualcomm/Llama-v3.2-1B-Instruct)


출처: `/home/ondevice-ai/aiwork/results/dev/ci-queue/mini/ci-queue-20261113_1610` 아래 각 조건 폴더 (표의 result_dir 열은 `/home/ondevice-ai/aiwork/results/dev/ci-queue/mini/ci-queue-20261113_1610/analysis`의 CSV에 있음)
