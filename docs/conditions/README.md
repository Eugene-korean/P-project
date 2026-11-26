# 실험 조건 목록

> 자동 생성 문서. `configs/` 아래 JSON에서 만들어진다. 고치려면 JSON을 고치고 push한다.
> main에 `configs/**.json`을 push하면 공용 PC에서 그 파일이 자동 실행되고, 이 문서도 다시 만들어진다.

phase 이름을 누르면 조건별 상세가 나온다. 측정 횟수 = 모델 수 × 길이 개수 × 반복 (한 번마다 재계산·저장·복원을 모두 잰다).

| phase | 파일 | stage | 제목 | 조건 수 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- |
| [check](check.md) | `configs/check/D1.json` | D1 | 기준선 (테스트) | 1 | 1 |
| [check](check.md) | `configs/check/D2.json` | D2 | CPU 변경 (테스트) | 1 | 1 |
| [check](check.md) | `configs/check/D3.json` | D3 | 메모리 상한 (테스트) | 1 | 1 |
| [check](check.md) | `configs/check/D4.json` | D4 | 저장장치 읽기 상한 (테스트) | 1 | 1 |
| [check](check.md) | `configs/check/D5.json` | D5 | 모델·길이 변경 (테스트) | 1 | 1 |
| [test](test.md) | `configs/test/D1.json` | D1 | 메모리 상한에 따른 KV Cache 성능 비교 | 6 | 6 |
