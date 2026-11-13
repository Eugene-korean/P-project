# test 조건

> 자동 생성 문서. `configs/` 아래 JSON에서 만들어진다. 고치려면 JSON을 고치고 push한다.
> main에 `configs/**.json`을 push하면 공용 PC에서 그 파일이 자동 실행되고, 이 문서도 다시 만들어진다.

[← 전체 목록](README.md)

## `configs/test/smoke.json`

제목: 동작 확인용 (1~2분)

목적: Actions·queue 설정이 제대로 도는지만 확인. 결과는 분석에 쓰지 않음

공통 설정: model=qwen, storage=raw, cache=cold, evict=drop, warmup=1, n_predict=8, repeats=1, measure_disk=True, measure_disk_mb=32, server_verbosity=4

| 조건 | 그룹 | 모델 | 길이 | 반복 | 바꾼 값 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- | --- |
| q16_64 |  | qwen | 16,64 | 1 | (공통 설정 그대로) | 2 |
