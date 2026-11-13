# mini 조건

> 자동 생성 문서. `configs/` 아래 JSON에서 만들어진다. 고치려면 JSON을 고치고 push한다.
> main에 `configs/**.json`을 push하면 공용 PC에서 그 파일이 자동 실행되고, 이 문서도 다시 만들어진다.

[← 전체 목록](README.md)

## `configs/mini/D1.json`

제목: 테스트: 제한 없는 기준선

목적: 자동 실행·합치기·분석 확인용 (결과는 쓰지 않음)

공통 설정: model=qwen, storage=raw, cache=cold,warm, evict=drop, warmup=1, n_predict=8, repeats=1, measure_disk=True, measure_disk_mb=64, server_verbosity=4

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| nolimit |  | qwen | 16,256,1024 | 1 | (공통 설정 그대로) | 3 |

## `configs/mini/D2.json`

제목: 테스트: 저장장치 속도만 변경

목적: 자동 실행·합치기·분석 확인용 (결과는 쓰지 않음)

공통 설정: model=qwen, storage=raw, cache=cold, evict=drop, warmup=1, n_predict=8, repeats=1, measure_disk=True, lengths=16,256,1024, server_verbosity=4

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| read5M |  | qwen | 16,256 | 1 | io_read=5M, measure_disk_mb=32 | 2 |
| read20M |  | qwen | 16,256,1024 | 1 | io_read=20M, measure_disk_mb=128 | 3 |
| read44M |  | qwen | 16,256,1024 | 1 | io_read=44M, measure_disk_mb=128 | 3 |
| nolimit |  | qwen | 16,256,1024 | 1 | measure_disk_mb=64 | 3 |
| ramdisk |  | qwen | 16,256,1024 | 1 | kv_dir=/dev/shm/kvcache, cache=warm, measure_disk_mb=64 | 3 |

## `configs/mini/D3.json`

제목: 테스트: CPU만 변경

목적: 자동 실행·합치기·분석 확인용 (결과는 쓰지 않음)

공통 설정: model=qwen, storage=raw, cache=cold, evict=drop, warmup=1, n_predict=8, repeats=1, measure_disk=True, measure_disk_mb=64, lengths=16,256,1024, server_verbosity=4

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| t4_f3600 | a | qwen | 16,256,1024 | 1 | threads=4, cores=4, max_freq=3600 | 3 |
| t8_f3600 | a,b | qwen | 16,256,1024 | 1 | threads=8, cores=8, max_freq=3600 | 3 |
| t8_f1500 | b | qwen | 16,256,1024 | 1 | threads=8, cores=8, max_freq=1500 | 3 |

## `configs/mini/D4.json`

제목: 테스트: 메모리

목적: 자동 실행·합치기·분석 확인용 (결과는 쓰지 않음)

공통 설정: model=qwen, storage=raw, cache=cold, evict=drop, warmup=1, n_predict=8, repeats=1, measure_disk=True, measure_disk_mb=64, lengths=1024, server_verbosity=4, drop_caches_before_server=True

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| idle_ctx1024 | ctx | qwen | 1024 | 1 | idle_only=True, ctx=1024 | 0 |
| idle_ctx1024_mem1.5G | ctx | qwen | 1024 | 1 | idle_only=True, ctx=1024, mem_limit=1536M, mem_high=1152M, swap_max=1G | 0 |
| mem2G |  | qwen | 1024 | 1 | mem_limit=2G, mem_high=1536M, swap_max=1G | 1 |
| mem1.5G |  | qwen | 1024 | 1 | mem_limit=1536M, mem_high=1152M, swap_max=1G | 1 |

## `configs/mini/D5.json`

제목: 테스트: 저사양 기기 프리셋

목적: 자동 실행·합치기·분석 확인용 (결과는 쓰지 않음)

공통 설정: model=qwen, storage=raw, cache=cold,warm, evict=drop, warmup=1, n_predict=8, repeats=1, measure_disk=True, lengths=16,256,1024, server_verbosity=4

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| rpi_like | b | qwen | 16,256,1024 | 1 | threads=4, cores=4, max_freq=1500, io_read=44M, io_write=20M, measure_disk_mb=128 | 3 |
