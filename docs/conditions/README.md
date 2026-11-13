# 실험 조건 목록

> 자동 생성 문서. `configs/` 아래 JSON에서 만들어진다. 고치려면 JSON을 고치고 push한다.
> main에 `configs/**.json`을 push하면 공용 PC에서 그 파일이 자동 실행되고, 이 문서도 다시 만들어진다.

phase 이름을 누르면 조건별 상세가 나온다. 측정 횟수 = 모델 수 × 길이 개수 × 반복 (한 번마다 재계산·저장·복원을 모두 잰다).

| phase | 파일 | stage | 제목 | 조건 수 | 측정 횟수 |
| --- | --- | --- | --- | --- | --- |
| [mini](mini.md) | `configs/mini/D1.json` | D1 | 테스트: 제한 없는 기준선 | 1 | 3 |
| [mini](mini.md) | `configs/mini/D2.json` | D2 | 테스트: 저장장치 속도만 변경 | 5 | 14 |
| [mini](mini.md) | `configs/mini/D3.json` | D3 | 테스트: CPU만 변경 | 3 | 9 |
| [mini](mini.md) | `configs/mini/D4.json` | D4 | 테스트: 메모리 | 4 | 2 |
| [mini](mini.md) | `configs/mini/D5.json` | D5 | 테스트: 저사양 기기 프리셋 | 1 | 3 |
| [phase2](phase2.md) | `configs/phase2/D1.json` | D1 | 제한 없는 기준선 | 1 | 90 |
| [phase2](phase2.md) | `configs/phase2/D2.json` | D2 | 저장장치 속도만 변경 | 7 | 310 |
| [phase2](phase2.md) | `configs/phase2/D3.json` | D3 | CPU만 변경 | 5 | 200 |
| [phase2](phase2.md) | `configs/phase2/D4.json` | D4 | 메모리 사용량과 메모리 압박 | 10 | 80 |
| [phase2](phase2.md) | `configs/phase2/D5.json` | D5 | 저사양 기기 프리셋 | 2 | 80 |
| [test](test.md) | `configs/test/smoke.json` | smoke | 동작 확인용 (1\~2분) | 1 | 2 |
