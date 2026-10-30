# 추가 Skill 설계 문서

- 작성일: 2026-10-30
- 대상 시험: SK하이닉스 AI 해커톤 2차 예선, 2026-10-31(토)
- 선행 문서: `2026-10-28-hackathon-agent-kit-design.md`

기존 Skill 6개(`task-router`, `tdd-automator`, `algorithm-optimizer`, `submission-validator`, `implementation-review`, `benchmark`)에 비어 있는 영역만 메운다. 새 Skill 2개를 추가하고 기존 Skill 2개를 보강해 총 8개로 만든다.

---

## 1. 확정된 결정

| 항목 | 결정 |
|---|---|
| 과제 유형 가정 | 미상(범용). 웹·데이터 전용 Skill은 만들지 않는다. 환경 확인은 기존 프로필(`web`, `data`)이 맡는다 |
| 접근 방식 | 공개 저장소에서 골라 가져와 시험 조건에 맞게 축약한다. 원본 그대로 복사하지 않는다 |
| 새 Skill | `systematic-debugging`(obra/superpowers에서 축약), `codebase-explorer`(직접 작성) |
| 보강 | `task-router`(선택 표, Plan, Decision log), `submission-validator`(verification-before-completion 규칙 흡수) |
| 제외 | `writing-plans`(task-router와 역할이 겹친다), 원본 부속 문서, 서브에이전트·worktree·커밋 관련 Skill |
| 호출 방식 | 새 Skill 둘 다 암묵 호출 허용(`agents/openai.yaml` 없음) |
| 필수 여부 | `required_skills`에 넣지 않는다. 누락은 PARTIAL이고 BLOCKED가 아니다 |
| description 예산 | 합계 2000자 상한을 유지한다. 기존 6개의 description을 다듬어 여유를 만든다 |

## 2. 공식 안내에서 나온 제약

| 안내 | 설계 반영 |
|---|---|
| AI 사용량과 활용 과정이 평가에 참고된다 | Skill 수와 본문 길이를 최소로 유지한다. description 합계 상한을 유지한다. 과정은 `TASK_BRIEF.md`의 `Decision log`에 남긴다 |
| 공개 저장소만 쓸 수 있고, 2차 예선 결과 통지 전까지 공개를 유지해야 한다 | 키트 저장소(`kimcheolhui9846/aaa`)와 출처 저장소(obra/superpowers) 모두 공개다. 결과 통지 전까지 키트 저장소를 비공개로 돌리지 않는다 |
| 결과물을 통째로 대체할 수 없다 | Skill에는 절차 지침만 둔다. 정답 템플릿이나 완성 코드 조각은 넣지 않는다 |
| Codex 버전 업데이트 금지 | Skill과 키트 어디에도 Codex를 설치하거나 업데이트하라는 지시를 두지 않는다(2026-10-30 grep으로 키트에 없음을 확인) |
| 사용 자료가 검토 대상이다 | `THIRD_PARTY_NOTICES.md`에 출처, 커밋, 라이선스를 남긴다 |

## 3. 파일 구조

```
.agents/skills/
  systematic-debugging/
    SKILL.md              # 40줄 안팎
    examples/example.md   # 가상 버그 하나로 절차를 시연
  codebase-explorer/
    SKILL.md              # 40줄 안팎
    examples/example.md   # 가상 저장소 하나로 절차를 시연
THIRD_PARTY_NOTICES.md    # 키트 저장소 루트에만 둔다. 작업 공간에는 설치하지 않는다
```

- `references/languages.md`는 만들지 않는다. 언어별 명령은 `tdd-automator/references/languages.md`를 가리킨다.
- 설치·검증 코드(`kit/plan.py`, `kit/verify.py`)는 프로필의 목록을 따르므로 수정하지 않는다.
- `profiles/core.json`: `skills`에 두 Skill을 추가하고, description의 "six"를 "eight"로 바꾼다. 다른 프로필은 `core`를 상속하므로 따로 수정하지 않는다.

## 4. `systematic-debugging`

출처: obra/superpowers `skills/systematic-debugging/SKILL.md`, 커밋 `2ce8aa15d05bd57213e6f746f953aafb7ded7a8b`, MIT.

description(목표 약 240자, 한 줄, 큰따옴표):

> Use when a test fails, output is wrong, or the program crashes and the cause is not yet known - finds the root cause before changing code. Do NOT use for failures whose cause is already obvious, or for performance problems (use algorithm-optimizer).

본문 단계:

1. **재현**: 실패를 다시 일으키는 가장 짧은 명령을 찾아 기록한다. 오류 메시지와 스택 트레이스는 끝까지 읽는다.
2. **범위 좁히기**: 최근 변경(`git diff`, 마지막으로 통과한 시점)과 정상 동작하는 비슷한 코드를 비교해 차이를 나열한다. 잘못된 값이 생긴 지점까지 거꾸로 추적한다.
3. **가설 하나, 최소 변경**: "X 때문에 Y다"를 한 문장으로 쓰고, 그것만 확인하는 가장 작은 변경이나 출력문으로 검증한다. 틀리면 2단계로 돌아간다.
4. **수정**: 실패를 재현하는 테스트를 먼저 추가하고(`tdd-automator` 방식), 원인 하나만 고친 뒤 전체 테스트를 다시 돌린다.
5. **기록**: `TASK_BRIEF.md`의 `Decision log`에 `원인 -> 수정 -> 근거`를 한 줄로 쓴다.

규칙:

- 원인을 찾기 전에는 코드를 바꿔 보지 않는다.
- 수정이 3번 실패하면 멈추고, 지금까지의 가설과 증거를 사용자에게 보고한다.
- 임시 디버그 출력은 끝나면 지운다.
- 파일 끝에 출처 한 줄: `Adapted from obra/superpowers (MIT). See THIRD_PARTY_NOTICES.md in the kit repository.`

원본에서 빼는 것: 부속 문서 3개(`root-cause-tracing.md`, `defense-in-depth.md`, `condition-based-waiting.md`), 다른 superpowers Skill 참조, 대화 상대 신호 등 Claude 대화 전용 문구.

## 5. `codebase-explorer`

직접 작성한다. 출처 고지는 필요 없다.

description(목표 약 230자):

> Use when the task gives an existing repository to modify or extend - maps entry points, build and test commands and the code relevant to the task before any edit. Do NOT use for tasks that start from an empty workspace or a single file.

본문 단계:

1. **겉부터 보기**: README, 의존성 파일(`pyproject.toml`, `package.json` 등), 최상위 폴더 구조만 읽는다. 파일을 통째로 읽지 않는다.
2. **실행·테스트 명령 확정**: 수정 전에 기존 테스트를 한 번 돌려 기준선(통과·실패 수)을 `TASK_BRIEF.md`에 기록한다.
3. **관련 코드 찾기**: 과제의 키워드로 검색해 진입점부터 해당 기능까지의 경로를 `파일:줄`로 짧게 정리한다.
4. **수정 범위 선언**: 바꿀 파일과 바꾸지 않을 파일을 `TASK_BRIEF.md`에 적는다. 기존 코드 스타일(이름 짓기, 오류 처리)을 따른다.

규칙: 과제와 무관한 리팩터링이나 포맷 변경을 하지 않는다. 의존성 추가나 업그레이드는 과제가 요구할 때만 한다.

## 6. 기존 Skill 보강

### `task-router`

- 선택 표에 두 줄을 추가한다.
  - 주어진 기존 저장소를 수정하거나 확장하는 과제 → `codebase-explorer`
  - 테스트 실패나 원인 모를 오류 → `systematic-debugging`
- 템플릿에 두 섹션을 추가한다.
  - `## Plan`: 구현 순서 3~5줄
  - `## Decision log`: `- <what> -> <why> -> <evidence>`를 결정마다 한 줄씩
- 길이 규칙을 "Keep it under 40 lines, not counting the Decision log"로 바꾼다.
- 7단계(재읽기)에 "Append one Decision log line for each non-obvious decision"을 추가한다.

### `submission-validator`

verification-before-completion(obra/superpowers, MIT)의 규칙을 흡수한다.

- 이번 검증에서 직접 실행한 명령의 출력만 증거로 인정한다. 앞서 돌린 결과를 재사용하지 않는다.
- Result 값에 `NOT RUN`을 추가한다(PASS, FAIL, MANUAL, NOT RUN). 실행하지 못한 검사는 PASS로 쓰지 않는다.

## 7. description 예산

- 현재 합계는 1747자다. 새 Skill 2개(약 470자)를 더하면 기존 6개를 약 1530자 이하로 줄여야 한다.
- 각 description의 "Use when … / Do NOT use …" 구조와 트리거 조건은 유지하고, 겹치는 수식어만 걷어낸다.
- `benchmark`, `implementation-review`는 "Use only when explicitly invoked"로 시작해야 한다(기존 테스트가 검사한다).
- 8개 합계가 2000자 이하인지는 `test_total_description_budget`이 강제한다.

## 8. 출처 고지

`THIRD_PARTY_NOTICES.md`(키트 저장소 루트)에 다음을 둔다.

- 저장소: `https://github.com/obra/superpowers`
- 커밋: `2ce8aa15d05bd57213e6f746f953aafb7ded7a8b`
- 사용 내역: `systematic-debugging`은 축약·수정해 가져왔다. `verification-before-completion`은 규칙만 `submission-validator`에 흡수했다.
- MIT 라이선스 전문(`Copyright (c) 2025 Jesse Vincent`).

## 9. 문서 동기화

- `README.md`: "Skill 6개" → "Skill 8개", 프로필 표의 "six" → "eight".
- `docs/TEST_REPORT.md`: Skill 개수와 수동 확인 항목(Codex `/skills`에 8개 표시)을 갱신한다.

## 10. 검증

자동:

- `tests/test_skills.py`의 `ALL`, `tests/test_profiles.py`의 `ALL_SKILLS`에 두 Skill을 추가한다. 기존 검사(frontmatter 유효성, "Do NOT use" 문구, 한 줄 description, 예제 존재, 폴더 목록 일치, 예산)를 새 Skill에도 적용한다.
- 새 테스트:
  - `task-router/SKILL.md`가 `codebase-explorer`, `systematic-debugging`, `## Plan`, `## Decision log`를 포함한다.
  - `submission-validator/SKILL.md`가 `NOT RUN`을 포함한다.
  - `THIRD_PARTY_NOTICES.md`가 존재하고 `MIT License`와 `Copyright (c) 2025 Jesse Vincent`를 포함한다.
  - `systematic-debugging/SKILL.md`가 출처 줄을 포함한다.
- `pytest` 전체와 `ruff check`를 실행한다.
- 빈 임시 폴더에 `bootstrap`을 실행해 `Status: READY`와 Skill 8개 설치를 확인한다.

수동(사용자):

- Codex에서 작업 폴더를 열고 `/skills`에 8개가 보이는지 확인한다.

## 11. 하지 않는 것

- 웹·데이터 전용 Skill, `writing-plans`, 원본 부속 문서.
- 설치·검증 코드(`kit/`) 변경.
- 커밋·push는 사용자 요청이 있을 때만 한다.
