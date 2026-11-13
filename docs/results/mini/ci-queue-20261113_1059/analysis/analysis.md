# 2차 실험 분석 결과

생성: 2026-11-13 11:01 · 입력: `/home/ondevice-ai/aiwork/results/dev/ci-queue/mini/ci-queue-20261113_1059/sweep_summary.csv`

단위: 시간 ms, 속도 MB/s(10^6 바이트), 메모리 MiB, s 바이트/토큰, r 토큰/s. "계산값"은 측정값으로 식을 계산한 것, "실측"은 측정에서 직접 읽은 것.

## 토큰당 KV 크기 s

| model | s_bytes_per_token | header_bytes | lengths |
| --- | --- | --- | --- |
| qwen | 12304.0 | 628.0 | 3 |


## 조건별 r, T0, B*, N*

| stage | condition | model | cache | status | r_fit_tok_s | B_MB_s | T0_ms | T0_source | Bstar_MB_s(계산값) | Nstar_tok(계산값) | Nstar_tok(실측 교차) | speedup_4096 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | nolimit | qwen | cold | ok | 464.46 | 387.67 | 15.43 | 자기 조건 16토큰 | 5.71 | 7.3 | <16 (모든 길이에서 배율>1) |  |
| D2 | nolimit | qwen | cold | ok | 469.28 | 511.32 | 15.95 | 자기 조건 16토큰 | 5.77 | 7.6 | <16 (모든 길이에서 배율>1) |  |
| D2 | ramdisk | qwen | warm | ok | 468.3 | 9287.84 | 13.57 | 자기 조건 16토큰 | 5.76 | 6.4 | <16 (모든 길이에서 배율>1) |  |
| D2 | read20M | qwen | cold | ok | 461.75 | 19.99 | 15.95 | D2/nolimit (io.max 소파일 통과 보정) | 5.68 | 10.3 | <16 (모든 길이에서 배율>1) |  |
| D2 | read44M | qwen | cold | ok | 466.91 | 44.57 | 15.95 | D2/nolimit (io.max 소파일 통과 보정) | 5.74 | 8.5 | <16 (모든 길이에서 배율>1) |  |
| D2 | read5M | qwen | cold | ok | 509.14 | 4.99 | 15.95 | D2/nolimit (io.max 소파일 통과 보정) | 6.26 | ∞ | 147.7 |  |
| D3 | t4_f3600 | qwen | cold | ok | 249.62 | 262.51 | 17.4 | 자기 조건 16토큰 | 3.07 | 4.4 | <16 (모든 길이에서 배율>1) |  |
| D3 | t8_f1500 | qwen | cold | ok | 197.04 | 396.07 | 26.9 | 자기 조건 16토큰 | 2.42 | 5.3 | <16 (모든 길이에서 배율>1) |  |
| D3 | t8_f3600 | qwen | cold | ok | 465.74 | 502.71 | 16.91 | 자기 조건 16토큰 | 5.73 | 8.0 | <16 (모든 길이에서 배율>1) |  |
| D4 | mem1.5G | qwen | cold | ok |  | 487.82 |  |  |  |  | <1024 (모든 길이에서 배율>1) |  |
| D4 | mem2G | qwen | cold | ok |  | 318.36 |  |  |  |  | <1024 (모든 길이에서 배율>1) |  |
| D5 | rpi_like | qwen | cold | ok | 104.18 | 44.49 | 27.52 | 자기 조건 16토큰 | 1.28 | 3.0 | <16 (모든 길이에서 배율>1) |  |


## D2 손익분기식 검증 (B* 예측 vs 실측 교차)

| model | n_tokens | B_cross_MB_s(실측 보간) | Bstar_MB_s(계산값) | Bstar_T0_MB_s(계산값) | err_Bstar_% | err_Bstar_T0_% | speedup_by_B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| qwen | 16 | <4.99 (최저 B에서도 배율 2.23) | 4.76 | 7.74 |  |  | 5.0MB/s→x2.23; 20.0MB/s→x2.67; 44.6MB/s→x1.48; 511.3MB/s→x2.53 |
| qwen | 256 | 5.91 | 6.16 | 6.36 | 4.2 | 7.6 | 5.0MB/s→x0.82; 20.0MB/s→x4.17; 44.6MB/s→x23.14; 511.3MB/s→x22.09 |
| qwen | 1024 | <19.99 (최저 B에서도 배율 3.52) | 5.79 | 5.83 |  |  | 20.0MB/s→x3.52; 44.6MB/s→x9.4; 511.3MB/s→x52.63 |


## 메모리 (제한 없음): RSS 증가 vs 이론 KV 크기

| stage | condition | model | cache | n_tokens | rss_increase_MiB | kv_theory_MiB(계산값) |
| --- | --- | --- | --- | --- | --- | --- |
| D1 | nolimit | qwen | cold | 16 | 48.4 | 0.2 |
| D1 | nolimit | qwen | cold | 256 | 49.0 | 3.0 |
| D1 | nolimit | qwen | cold | 1024 | 49.6 | 12.0 |
| D1 | nolimit | qwen | warm | 16 | 48.4 | 0.2 |
| D1 | nolimit | qwen | warm | 256 | 49.0 | 3.0 |
| D1 | nolimit | qwen | warm | 1024 | 49.6 | 12.0 |
| D2 | nolimit | qwen | cold | 16 | 48.4 | 0.2 |
| D2 | nolimit | qwen | cold | 256 | 49.0 | 3.0 |
| D2 | nolimit | qwen | cold | 1024 | 49.6 | 12.0 |
| D2 | ramdisk | qwen | warm | 16 | 48.4 | 0.2 |
| D2 | ramdisk | qwen | warm | 256 | 49.0 | 3.0 |
| D2 | ramdisk | qwen | warm | 1024 | 49.6 | 12.0 |
| D2 | read20M | qwen | cold | 16 | 48.4 | 0.2 |
| D2 | read20M | qwen | cold | 256 | 49.0 | 3.0 |
| D2 | read20M | qwen | cold | 1024 | 49.6 | 12.0 |
| D2 | read44M | qwen | cold | 16 | 48.4 | 0.2 |
| D2 | read44M | qwen | cold | 256 | 49.0 | 3.0 |
| D2 | read44M | qwen | cold | 1024 | 49.6 | 12.0 |
| D2 | read5M | qwen | cold | 16 | 30.5 | 0.2 |
| D2 | read5M | qwen | cold | 256 | 30.5 | 3.0 |
| D3 | t4_f3600 | qwen | cold | 16 | 46.9 | 0.2 |
| D3 | t4_f3600 | qwen | cold | 256 | 47.1 | 3.0 |
| D3 | t4_f3600 | qwen | cold | 1024 | 47.7 | 12.0 |
| D3 | t8_f1500 | qwen | cold | 16 | 48.4 | 0.2 |
| D3 | t8_f1500 | qwen | cold | 256 | 49.0 | 3.0 |
| D3 | t8_f1500 | qwen | cold | 1024 | 49.6 | 12.0 |
| D3 | t8_f3600 | qwen | cold | 16 | 48.4 | 0.2 |
| D3 | t8_f3600 | qwen | cold | 256 | 49.0 | 3.0 |
| D3 | t8_f3600 | qwen | cold | 1024 | 49.6 | 12.0 |
| D5 | rpi_like | qwen | cold | 16 | 47.0 | 0.2 |
| D5 | rpi_like | qwen | cold | 256 | 47.2 | 3.0 |
| D5 | rpi_like | qwen | cold | 1024 | 47.8 | 12.0 |
| D5 | rpi_like | qwen | warm | 16 | 47.0 | 0.2 |
| D5 | rpi_like | qwen | warm | 256 | 47.2 | 3.0 |
| D5 | rpi_like | qwen | warm | 1024 | 47.8 | 12.0 |


## D4 컨텍스트 크기별 대화 없을 때 메모리 (서버 시작 전 캐시 비움)

| model | mem_limit | ctx | kv_buffer_MiB | kv_theory_MiB(계산값) | compute_buffer_MiB | repack_buffer_MiB | rss_MiB | anon_MiB | file_MiB | swap_MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen | 1536M | 1024 | 12.0 | 12.0 | 38.27 | 28.05 | 576.1 | 95.4 | 480.7 | 0.0 |
| qwen | 없음 | 1024 | 12.0 | 12.0 | 38.27 | 28.05 | 576.1 | 95.4 | 480.7 | 0.0 |


## D4 메모리 압박

| model | mem_limit | status | n_tokens | runs | recompute_ms | resume_total_ms | speedup | swap_after_restore_MiB_max | vmstat_si_KiB | vmstat_so_KiB | all_match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen | 1536M | ok | 1024 | 1 | 2171.25 | 74.45 | 29.16 | 0.0 | 16 | 10 | True |
| qwen | 2G | ok | 1024 | 1 | 2175.42 | 93.13 | 23.36 | 0.0 | 16 | 10 | True |


## 저장 비용과 본전 재사용 횟수

| stage | condition | model | cache | n_tokens | save_total_ms | resume_total_ms | recompute_ms | breakeven_reuse |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | nolimit | qwen | cold | 16 | 12.88 | 15.94 | 43.63 | 1.041 |
| D1 | nolimit | qwen | cold | 256 | 21.71 | 24.35 | 513.88 | 0.094 |
| D1 | nolimit | qwen | cold | 1024 | 50.8 | 43.56 | 2200.06 | 0.044 |
| D2 | nolimit | qwen | cold | 16 | 15.29 | 16.34 | 41.39 | 1.262 |
| D2 | nolimit | qwen | cold | 256 | 19.45 | 23.15 | 511.39 | 0.087 |
| D2 | nolimit | qwen | cold | 1024 | 46.65 | 41.37 | 2177.03 | 0.041 |
| D2 | ramdisk | qwen | warm | 16 | 0.18 | 13.6 | 47.63 | 0.405 |
| D2 | ramdisk | qwen | warm | 256 | 1.02 | 14.99 | 518.6 | 0.032 |
| D2 | ramdisk | qwen | warm | 1024 | 3.91 | 18.44 | 2187.74 | 0.01 |
| D2 | read20M | qwen | cold | 16 | 8.66 | 15.72 | 41.99 | 0.928 |
| D2 | read20M | qwen | cold | 256 | 22.18 | 123.35 | 514.72 | 0.372 |
| D2 | read20M | qwen | cold | 1024 | 60.06 | 628.35 | 2211.01 | 0.435 |
| D2 | read44M | qwen | cold | 16 | 6.3 | 27.96 | 41.45 | 2.54 |
| D2 | read44M | qwen | cold | 256 | 23.25 | 22.05 | 510.23 | 0.093 |
| D2 | read44M | qwen | cold | 1024 | 44.93 | 232.67 | 2186.89 | 0.142 |
| D2 | read5M | qwen | cold | 16 | 14.06 | 18.39 | 40.98 | 1.437 |
| D2 | read5M | qwen | cold | 256 | 21.29 | 627.04 | 512.36 |  |
| D3 | t4_f3600 | qwen | cold | 16 | 10.44 | 18.15 | 71.43 | 0.537 |
| D3 | t4_f3600 | qwen | cold | 256 | 16.5 | 23.97 | 975.49 | 0.043 |
| D3 | t4_f3600 | qwen | cold | 1024 | 52.69 | 55.81 | 4092.43 | 0.027 |
| D3 | t8_f1500 | qwen | cold | 16 | 20.21 | 27.4 | 95.54 | 0.699 |
| D3 | t8_f1500 | qwen | cold | 256 | 23.64 | 41.8 | 1219.87 | 0.056 |
| D3 | t8_f1500 | qwen | cold | 1024 | 62.14 | 90.62 | 5183.35 | 0.03 |
| D3 | t8_f3600 | qwen | cold | 16 | 11.09 | 17.31 | 41.03 | 1.197 |
| D3 | t8_f3600 | qwen | cold | 256 | 22.78 | 22.16 | 510.06 | 0.092 |
| D3 | t8_f3600 | qwen | cold | 1024 | 46.11 | 66.63 | 2191.59 | 0.053 |
| D4 | mem1.5G | qwen | cold | 1024 | 58.63 | 74.45 | 2171.25 | 0.064 |
| D4 | mem2G | qwen | cold | 1024 | 56.08 | 93.13 | 2175.42 | 0.072 |
| D5 | rpi_like | qwen | cold | 16 | 6.59 | 31.96 | 164.86 | 0.29 |
| D5 | rpi_like | qwen | cold | 256 | 186.82 | 41.13 | 2336.76 | 0.099 |
| D5 | rpi_like | qwen | cold | 1024 | 665.39 | 256.33 | 9800.97 | 0.097 |


## 모델 비교 (Qwen vs Llama)

_(데이터 없음)_


## 기기별 판단 기준 (실측·예측 구분)

| device | model | kind | prefill_tok_s | read_MB_s | write_MB_s | Bstar_MB_s | T0_ms | Nstar_tok | recompute_4096_ms | load_4096_ms | save_4096_ms | speedup_4096 | criterion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 공용 PC (i7-9700K 8스레드 3.6GHz, SATA SSD) | qwen | 실측 | 464.46 | 387.67 |  | 5.71 | 15.43 | 7.3 |  |  |  |  | 측정한 모든 길이(16\~4,096토큰)에서 저장·로드가 이득 → 항상 저장 (계산 경계 N*≈7.3토큰, 읽기 5.71MB/s 이하로 느려지면 버리기) |
| 라즈베리파이 흉내 (4코어 1.5GHz, 읽기 44MB/s·쓰기 20MB/s) | qwen | 실측 | 104.18 | 44.49 |  | 1.28 | 27.52 | 3.0 |  |  |  |  | 측정한 모든 길이(16\~4,096토큰)에서 저장·로드가 이득 → 항상 저장 (계산 경계 N*≈3.0토큰, 읽기 1.28MB/s 이하로 느려지면 버리기) |
| Galaxy S25 (Snapdragon 8 Elite for Galaxy) | qwen | 공개 자료 없음 |  |  |  |  |  |  |  |  |  |  | Qwen2.5-0.5B의 Snapdragon 8 Elite for Galaxy Prefill 공개값을 찾지 못함 (지어내지 않음) |
| iPhone 16 Pro | qwen | 공개 자료 없음 |  |  |  |  |  |  |  |  |  |  | 이 모델의 iPhone 16 Pro Prefill 속도와 저장장치 읽기·쓰기 속도 공개 자료 없음 (지어내지 않음) |


Galaxy S25 예측 근거: Qualcomm AI Hub Llama-v3.2-1B-Instruct 모델 카드, 'Snapdragon 8 Elite For Galaxy Mobile', GENIE 런타임, 컨텍스트 4096: 4,096토큰 프롬프트 TTFT 1.01초(w4a16)\~2.03초(w4), 128토큰 이하 프롬프트(처리 1회) 0.03\~0.06초 (https://huggingface.co/qualcomm/Llama-v3.2-1B-Instruct)


출처: `/home/ondevice-ai/aiwork/results/dev/ci-queue/mini/ci-queue-20261113_1059` 아래 각 조건 폴더 (표의 result_dir 열은 `/home/ondevice-ai/aiwork/results/dev/ci-queue/mini/ci-queue-20261113_1059/analysis`의 CSV에 있음)
