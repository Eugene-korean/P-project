# check 조건

> 자동 생성 문서. `configs/` 아래 JSON에서 만들어진다. 고치려면 JSON을 고치고 push한다.
> main에 `configs/**.json`을 push하면 공용 PC에서 그 파일이 자동 실행되고, 이 문서도 다시 만들어진다.

[← 전체 목록](README.md)

## `configs/check/D1.json`

제목: 기준선 (테스트)

목적: 자동 실행 경로 확인. 제한 없음

공통 설정: model=qwen, lengths=4096, repeats=1, threads=8, cores=8, storage=raw,lz4, cache=cold, evict=drop, n_predict=32, warmup=2, measure_disk=True, measure_disk_mb=64, ctx=4192, server_verbosity=4

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| nolimit |  | qwen | 4096 | 1 | (공통 설정 그대로) | 1 |

## `configs/check/D2.json`

제목: CPU 변경 (테스트)

목적: 스레드·코어 4개가 적용되는지

공통 설정: model=qwen, lengths=4096, repeats=1, threads=8, cores=8, storage=raw,lz4, cache=cold, evict=drop, n_predict=32, warmup=2, measure_disk=True, measure_disk_mb=64, ctx=4192, server_verbosity=4

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| cores4 |  | qwen | 4096 | 1 | threads=4, cores=4 | 1 |

## `configs/check/D3.json`

제목: 메모리 상한 (테스트)

목적: 메모리 상한·swap이 적용되는지

공통 설정: model=qwen, lengths=4096, repeats=1, threads=8, cores=8, storage=raw,lz4, cache=cold, evict=drop, n_predict=32, warmup=2, measure_disk=True, measure_disk_mb=64, ctx=4192, server_verbosity=4

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| mem2G |  | qwen | 4096 | 1 | mem_limit=2G, mem_high=1536M, swap_max=1G | 1 |

## `configs/check/D4.json`

제목: 저장장치 읽기 상한 (테스트)

목적: SSD 읽기 속도 상한이 적용되는지

공통 설정: model=qwen, lengths=4096, repeats=1, threads=8, cores=8, storage=raw,lz4, cache=cold, evict=drop, n_predict=32, warmup=2, measure_disk=True, measure_disk_mb=64, ctx=4192, server_verbosity=4

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| read100M |  | qwen | 4096 | 1 | io_read=100M | 1 |

## `configs/check/D5.json`

제목: 모델·길이 변경 (테스트)

목적: common을 조건에서 덮어쓰기가 되는지

공통 설정: model=qwen, lengths=4096, repeats=1, threads=8, cores=8, storage=raw,lz4, cache=cold, evict=drop, n_predict=32, warmup=2, measure_disk=True, measure_disk_mb=64, ctx=4192, server_verbosity=4

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| llama1024 |  | llama | 1024 | 1 | model=llama, lengths=1024 | 1 |
