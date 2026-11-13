# phase2 조건

> 자동 생성 문서. `configs/` 아래 JSON에서 만들어진다. 고치려면 JSON을 고치고 push한다.
> main에 `configs/**.json`을 push하면 공용 PC에서 그 파일이 자동 실행되고, 이 문서도 다시 만들어진다.

[← 전체 목록](README.md)

## `configs/phase2/D1.json`

제목: 제한 없는 기준선

목적: CPU·메모리·저장장치 제한을 모두 푼 원래 성능 (PC·노트북 등급 기준점)

공통 설정: model=both, storage=raw, cache=cold,warm, evict=drop, warmup=2, n_predict=32, repeats=5, measure_disk=True, ctx=4192, server_verbosity=4

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| nolimit |  | both | 16,32,64,128,256,512,1024,2048,4096 | 5 | (공통 설정 그대로) | 90 |

참고: 실제 온디바이스 세션 한도(약 4,096토큰)에 맞춰 처리 길이 최대 4096, 컨텍스트 4192 고정 (llama.cpp가 256 배수로 올려 실제 4352). -lv 4로 KV 버퍼 크기를 로그·meta에 기록

## `configs/phase2/D2.json`

제목: 저장장치 속도만 변경

목적: 로드 시간이 저장장치에만 좌우되는지, 손익분기점 직접 관측. 쓰기 제한 없음, CPU 제한 없음

공통 설정: model=both, storage=raw, cache=cold, evict=drop, warmup=2, n_predict=32, repeats=5, measure_disk=True, lengths=16,64,256,1024,4096, ctx=4192, server_verbosity=4

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| read5M |  | both | 16,64,256 | 5 | io_read=5M, measure_disk_mb=32 | 30 |
| read10M |  | both | 16,64,256 | 5 | io_read=10M, measure_disk_mb=64 | 30 |
| read20M |  | both | 16,64,256,1024,4096 | 5 | io_read=20M, measure_disk_mb=128 | 50 |
| read44M |  | both | 16,64,256,1024,4096 | 5 | io_read=44M, measure_disk_mb=128 | 50 |
| read100M |  | both | 16,64,256,1024,4096 | 5 | io_read=100M | 50 |
| nolimit |  | both | 16,64,256,1024,4096 | 5 | (공통 설정 그대로) | 50 |
| ramdisk |  | both | 16,64,256,1024,4096 | 5 | kv_dir=/dev/shm/kvcache, cache=warm | 50 |

참고: 실제 온디바이스 세션 한도(약 4,096토큰)에 맞춰 처리 길이 최대 4096, 컨텍스트 4192 고정 (llama.cpp가 256 배수로 올려 실제 4352). -lv 4로 KV 버퍼 크기를 로그·meta에 기록

## `configs/phase2/D3.json`

제목: CPU만 변경

목적: Prefill 시간이 CPU에만 좌우되는지, B*가 r에 비례하는지. 저장장치 제한 없음

공통 설정: model=both, storage=raw, cache=cold, evict=drop, warmup=2, n_predict=32, repeats=5, measure_disk=True, lengths=16,256,1024,4096, ctx=4192, server_verbosity=4

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| t2_f3600 | a | both | 16,256,1024,4096 | 5 | threads=2, cores=2, max_freq=3600 | 40 |
| t4_f3600 | a | both | 16,256,1024,4096 | 5 | threads=4, cores=4, max_freq=3600 | 40 |
| t8_f3600 | a,b | both | 16,256,1024,4096 | 5 | threads=8, cores=8, max_freq=3600 | 40 |
| t8_f2400 | b | both | 16,256,1024,4096 | 5 | threads=8, cores=8, max_freq=2400 | 40 |
| t8_f1500 | b | both | 16,256,1024,4096 | 5 | threads=8, cores=8, max_freq=1500 | 40 |

참고: 실제 온디바이스 세션 한도(약 4,096토큰)에 맞춰 처리 길이 최대 4096, 컨텍스트 4192 고정 (llama.cpp가 256 배수로 올려 실제 4352). -lv 4로 KV 버퍼 크기를 로그·meta에 기록

## `configs/phase2/D4.json`

제목: 메모리 사용량과 메모리 압박

목적: 토큰 수별 실제 메모리 사용량, swap이 생기고 느려지는 지점 (두 모델 차이 포함). 제한 없음 RSS는 D1 재사용. 서버 시작 전 페이지 캐시를 비워 모델 파일 메모리도 항상 서버의 상한 안에서 계산. idle_* 조건은 --ctx 1024·2048·4096별 대화 없을 때 RSS·KV 버퍼·swap

공통 설정: model=both, storage=raw, cache=cold, evict=drop, warmup=2, n_predict=32, repeats=5, measure_disk=True, lengths=1024,4096, ctx=4192, server_verbosity=4, drop_caches_before_server=True

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| idle_ctx1024 | ctx | both | 1024,4096 | 1 | idle_only=True, ctx=1024 | 0 |
| idle_ctx2048 | ctx | both | 1024,4096 | 1 | idle_only=True, ctx=2048 | 0 |
| idle_ctx4096 | ctx | both | 1024,4096 | 1 | idle_only=True, ctx=4096 | 0 |
| idle_ctx1024_mem1.5G | ctx | both | 1024,4096 | 1 | idle_only=True, ctx=1024, mem_limit=1536M, mem_high=1152M, swap_max=1G | 0 |
| idle_ctx2048_mem1.5G | ctx | both | 1024,4096 | 1 | idle_only=True, ctx=2048, mem_limit=1536M, mem_high=1152M, swap_max=1G | 0 |
| idle_ctx4096_mem1.5G | ctx | both | 1024,4096 | 1 | idle_only=True, ctx=4096, mem_limit=1536M, mem_high=1152M, swap_max=1G | 0 |
| mem4G |  | both | 1024,4096 | 5 | mem_limit=4G, mem_high=3G, swap_max=1G | 20 |
| mem3G |  | both | 1024,4096 | 5 | mem_limit=3G, mem_high=2304M, swap_max=1G | 20 |
| mem2G |  | both | 1024,4096 | 5 | mem_limit=2G, mem_high=1536M, swap_max=1G | 20 |
| mem1.5G |  | both | 1024,4096 | 5 | mem_limit=1536M, mem_high=1152M, swap_max=1G | 20 |

참고: 실제 온디바이스 세션 한도(약 4,096토큰)에 맞춰 처리 길이 최대 4096, 컨텍스트 4192 고정 (llama.cpp가 256 배수로 올려 실제 4352). -lv 4로 KV 버퍼 크기를 로그·meta에 기록

## `configs/phase2/D5.json`

제목: 저사양 기기 프리셋

목적: (a) 1차 조건 재현 확인 (b) 라즈베리파이 흉내

공통 설정: model=both, storage=raw, cache=cold,warm, evict=drop, warmup=2, n_predict=32, repeats=5, measure_disk=True, lengths=16,256,1024,4096, ctx=4192, server_verbosity=4

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| phase1_repro | a | both | 16,256,1024,4096 | 5 | threads=4, cores=4, max_freq=2400, cpu_quota=300%, mem_limit=3G, mem_high=2G, swap_max=1G, io_read=100M, io_write=50M | 40 |
| rpi_like | b | both | 16,256,1024,4096 | 5 | threads=4, cores=4, max_freq=1500, io_read=44M, io_write=20M, measure_disk_mb=128 | 40 |

참고: 실제 온디바이스 세션 한도(약 4,096토큰)에 맞춰 처리 길이 최대 4096, 컨텍스트 4192 고정 (llama.cpp가 256 배수로 올려 실제 4352). -lv 4로 KV 버퍼 크기를 로그·meta에 기록
