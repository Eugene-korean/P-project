# 실험 조건(config) 작성 틀

```json
{
  "stage": "D1",
  "title": "메모리 상한만 변경",
  "purpose": "메모리를 줄일 때 다시 계산·불러오기 시간과 swap이 어떻게 바뀌는지",
  "common": {
    "model": "qwen", "lengths": "4096", "repeats": 5,
    "threads": 8, "cores": 8,
    "storage": "raw,lz4", "cache": "cold", "evict": "drop",
    "n_predict": 32, "warmup": 2,
    "measure_disk": true, "ctx": 4192, "server_verbosity": 4
  },
  "conditions": [
    {"name": "nolimit", "args": {}},
    {"name": "mem3G",   "args": {"mem_limit": "3G",    "mem_high": "2304M", "swap_max": "1G"}},
    {"name": "mem2G",   "args": {"mem_limit": "2G",    "mem_high": "1536M", "swap_max": "1G"}},
    {"name": "mem1.5G", "args": {"mem_limit": "1536M", "mem_high": "1152M", "swap_max": "1G"}}
  ]
}
```

---

## 설명

### 맨 위 칸

| 칸 | 뜻 |
| --- | --- |
| `stage` | 세트 번호. `D1`, `D2`… (이 이름일 때만 결과 표가 합쳐진다) |
| `title`, `purpose` | 세트 제목과 목적. 조건 문서(`docs/conditions/`)에 그대로 찍힌다 |

### `common` (이 세트의 모든 조건에 공통)

`common`은 그 세트의 기본값이다. 조건의 `args`에 같은 칸을 적으면 그 조건만 덮어쓴다.

**건드리지 않는 값** (측정 방식. 모든 세트에서 같아야 결과끼리 비교된다)

| 칸 | 값 | 뜻 |
| --- | --- | --- |
| `storage` | `raw,lz4` | 저장 방식. 매번 둘 다 측정 |
| `cache` | `cold` | 저장장치에서 읽기 |
| `evict` | `drop` | cold 만드는 방법. 전체 캐시 비우기 |
| `n_predict` | `32` | 복원 후 출력 비교용 생성 길이 |
| `warmup` | `2` | 측정 전 버리는 요청 수 |
| `measure_disk` | `true` | 시작할 때 저장장치 실제 읽기·쓰기 속도 기록 |
| `server_verbosity` | `4` | llama-server 로그 수준 (KV 버퍼 크기 기록용) |

적지 않은 값(최대 클럭, 사용률 상한, SSD 쓰기 상한)은 제한 없음.

**바꿀 수 있는 기본값** (평소엔 이 값. 실험 목적에 따라 `args`나 세트별 `common`에서 바꾼다)

| 칸 | 값 | 뜻 |
| --- | --- | --- |
| `model` | `qwen` | 모델. 하나로 고정해서 쓴다 |
| `lengths` | `4096` | 프롬프트 길이(토큰). 하나로 고정해서 쓴다. 길이 실험 때만 바꿈 |
| `repeats` | `5` | 같은 조건 반복 횟수. 5~10 |
| `threads`, `cores` | `8` | 스레드 수, 코어 개수. 물리 코어 8개 이하 |
| `ctx` | `4192` | 컨텍스트 크기(토큰). 서버가 KV 메모리를 이 크기만큼 **미리** 잡는다 (대화 길이와 상관없이). 평소엔 4192로 두고, **필요하면 조건(`args`)에서 바꿔 ctx 자체를 실험할 수 있다** (아래 참고) |

### `conditions` (조건마다 바꾸는 값)

| 칸 | 뜻 |
| --- | --- |
| `name` | 조건 이름. 영어·숫자만 (예: `mem2G`). 결과 폴더 이름이 된다 |
| `args` | 이 조건에서만 바꾸는 값. `common`을 덮어쓴다. 비우면(`{}`) `common` 그대로 |

`args`에 넣을 수 있는 값:

| 칸 | 범위 | 뜻 |
| --- | --- | --- |
| `threads`, `cores` | 1~8 | CPU |
| `mem_limit` | 512M~32G | 메모리 상한. 넘으면 swap으로 밀리거나 서버 종료 |
| `mem_high` | `mem_limit`의 75% | 완만한 상한. **직접 계산해서 적는다** (3G → 2304M, 2G → 1536M, 1.5G → 1152M, 1G → 768M) |
| `swap_max` | 0~8G | swap 허용량. `mem_limit`을 걸 때만 의미 있음 |
| `io_read` | 5M~2G | 실험 SSD 읽기 속도 상한 |
| `ctx` | 가장 긴 길이 + 33 이상, 모델 한도 이하 (qwen 약 32768, llama 약 131072) | 컨텍스트 크기. 크게 잡을수록 KV 메모리를 많이 미리 잡는다 |
| `idle_only` | `true` | 프롬프트 없이 서버만 띄워 메모리만 잰다 (ctx 실험용, 금방 끝남). `repeats: 1`과 함께 |
| `model`, `lengths`, `repeats` | | 위 "바꿀 수 있는 기본값" |

- `nolimit`(`args` 비움)을 비교 기준으로 세트마다 하나씩 넣는다.
- **ctx는 필요할 때만 조건으로 추가한다.** CPU·메모리·저장장치를 비교하는 세트에서는 모든 조건의 ctx가 같아야 메모리 수치를 비교할 수 있다 (`common`의 4192 그대로).
  ctx 자체를 볼 때는 조건마다 ctx만 바꾼다. 예: 메모리만 빠르게 보기
  ```json
  {"name": "idle_ctx8192",  "args": {"idle_only": true, "ctx": 8192,  "repeats": 1}},
  {"name": "idle_ctx16384", "args": {"idle_only": true, "ctx": 16384, "repeats": 1}},
  {"name": "idle_ctx32768", "args": {"idle_only": true, "ctx": 32768, "repeats": 1}}
  ```
  결과의 `kv_buffer_mib`(미리 잡은 KV), `idle_rss_mb`(실제 메모리), `idle_swap_mb`(swap으로 밀린 양)를 본다. `mem_limit`을 같이 걸면 어느 ctx부터 swap이 생기는지 볼 수 있다.

### 위치 · 주의

- 위치: `configs/<phase>/D1.json`
- main에 `configs/` 아래 `.json`을 push하면 **바로 공용 PC에서 실험이 시작된다.** push 전에 단톡 공지, `git pull` 먼저.
