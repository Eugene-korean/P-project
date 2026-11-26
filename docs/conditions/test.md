# test 조건

> 자동 생성 문서. `configs/` 아래 JSON에서 만들어진다. 고치려면 JSON을 고치고 push한다.
> main에 `configs/**.json`을 push하면 공용 PC에서 그 파일이 자동 실행되고, 이 문서도 다시 만들어진다.

[← 전체 목록](README.md)

## `configs/test/D1.json`

제목: 메모리 상한에 따른 KV Cache 성능 비교

목적: Swap 없이 메모리 상한 변화에 따른 재계산 및 복원 성능 분석

공통 설정: model=qwen, lengths=4096, repeats=1, threads=8, cores=8, storage=raw,lz4, cache=cold, evict=drop, n_predict=32, warmup=2, measure_disk=True, ctx=4192, server_verbosity=4, swap_max=0

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| nolimit |  | qwen | 4096 | 1 | (공통 설정 그대로) | 1 |
| mem4G |  | qwen | 4096 | 1 | mem_limit=4G | 1 |
| mem3G |  | qwen | 4096 | 1 | mem_limit=3G | 1 |
| mem2G |  | qwen | 4096 | 1 | mem_limit=2G | 1 |
| mem1G5 |  | qwen | 4096 | 1 | mem_limit=1536M | 1 |
| mem1G |  | qwen | 4096 | 1 | mem_limit=1G | 1 |
