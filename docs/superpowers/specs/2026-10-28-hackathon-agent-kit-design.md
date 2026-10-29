# Hackathon Agent Kit — 설계 문서

- 작성일: 2026-10-28
- 원본 지시서: `CLAUDE_CODE_HACKATHON_BOOTSTRAP_SPEC.md` (이하 "지시서")
- 대상 시험: SK하이닉스 AI 해커톤 2차 예선, 2026-10-31(토) 10:00~14:00
- 이 저장소는 **Claude Code로 사전 개발**한다. 시험 중에는 운영 환경이 제공하는 Codex만 사용한다.

이 문서는 지시서를 3일 일정에 맞게 좁히고, 브레인스토밍에서 확정한 결정을 기록한다. 지시서와 충돌하면 이 문서가 우선하며, 충돌 지점과 사유를 명시한다.

---

## 1. 확정된 결정

| 항목 | 결정 |
|---|---|
| 범위·우선순위 | 필수선: Skill + AGENTS.md + core bootstrap. 여유 시 지시서 전체(프로필·MCP·audit·문서)로 확장 |
| 과제 언어 | 미상. Skill 절차는 언어 중립, 예시는 Python 기본, 타 언어는 `references/languages.md` 대응표 |
| 문서 언어 | AGENTS.md·SKILL.md는 영어, README·docs는 한국어 |
| 구현 방식 | 얇은 셸 진입점(sh/ps1) + 표준 라이브러리 전용 Python 코어(`kit/`). Python 부재 시 셸 최소 배치 |
| 설치 범위 | 대상 작업 공간(`<target>/AGENTS.md`, `<target>/.agents/skills/`, `<target>/.codex/config.toml`)만. 사용자 전역은 건드리지 않음 |
| Skill 로드 검증 | 비대화형 검증 수단 없음 → `UNVERIFIED` + "TUI `/skills` 확인" 안내. READY를 막지 않음 |
| 시험 당일 태도 | 불러보고 안 되면 안 되는 대로 진행. 보고서는 "확인됨 / 직접 확인할 것"을 정확히 구분하는 것이 목적 |

## 2. 검증된 사실 (2026-10-28, codex-cli 0.164.0 및 공식 문서)

- Skill 탐색 경로: `$CWD/.agents/skills`, CWD에서 저장소 루트까지의 각 `.agents/skills`, `$HOME/.agents/skills`, `/etc/codex/skills`, 시스템 번들.
- `SKILL.md` frontmatter 필수 필드: `name`, `description`. 초기 Skill 목록 예산은 컨텍스트의 약 2% 또는 8,000자.
- 선택 파일 `agents/openai.yaml`의 `policy.allow_implicit_invocation: false` → 명시적 `$skill` 호출 시에만 실행.
- 프로젝트 설정 `.codex/config.toml`은 **신뢰된 프로젝트에서만** 로드된다. `[mcp_servers.<name>]` 키: `command`, `args`, `env`, `env_vars`, `cwd`, `enabled`, `required`, `startup_timeout_sec`, `tool_timeout_sec`, `enabled_tools`, `disabled_tools` 등. `url`은 원격(streamable HTTP) 전송.
- `codex mcp list --json` 존재 확인.
- `codex debug prompt-input`에는 Skill 목록이 나타나지 않음(임시 Skill로 확인). 이 버전은 Skill을 검색 도구로 노출하는 것으로 보인다 → Skill 로드는 비대화형 검증 불가.
- 시험 환경(Cofa) 관련 사항은 모두 미확인이다 → `docs/ASSUMPTIONS.md`에 `UNVERIFIED`로 기록.

## 3. 아키텍처

```
bootstrap.sh / bootstrap.ps1     인수 파싱, --help, Python 3.9+ 탐지 (KIT_PYTHON으로 재정의 가능)
  ├─ Python 있음 → python -m kit <args>
  └─ Python 없음 → 셸 최소 배치: 대상에 없으면 복사, 있으면 CONFLICT → PARTIAL(종료 1)

kit/                (Python 표준 라이브러리만 사용)
  cli.py        인수 → Options
  preflight.py  OS/셸/권한/쓰기 가능 여부, git·python·uv·node·npx·codex 버전 → EnvReport
  plan.py       프로필 + EnvReport → Action 목록 (dry-run은 출력 후 종료)
  register.py   AGENTS.md 보호 구간 병합, Skill 배치, .codex/config.toml 병합 (백업 포함)
  install.py    프로필 도구 설치 (uv tool → pip --user 순), offline이면 네트워크 동작 금지
  verify.py     정적 검사 + 도구 smoke test + MCP 핸드셰이크 + `codex mcp list --json`
  audit.py      manifest/allowlist 대조, 원격 URL·push·API 키 패턴 탐지
  report.py     요약 출력 + <target>/.kit/logs/ 에 마스킹된 로그
```

**지시서 대비 조정:** 지시서의 `scripts/*.py` 대신 `kit/` 패키지를 쓴다. import와 테스트가 단순해지기 때문이며, `docs/ARCHITECTURE.md`에 같은 사유를 기록한다. `scripts/install.py` → `kit/install.py`처럼 1:1 대응한다.

### 3.1 변경의 단일 경로

모든 변경은 `plan`이 만든 Action 목록을 통과한다.

- `--dry-run`: Action 목록(파일 생성 위치, 실행할 명령, 네트워크 접근 여부)을 출력하고 종료한다. 대상에 어떤 파일도 쓰지 않는다(`.kit/` 포함).
- `--verify-only`: register·install 단계를 건너뛰고 verify·audit·report만 실행한다. 로그 파일 외에는 쓰지 않는다.
- `--no-mcp`: MCP 관련 Action을 생성하지 않는다.
- `--offline`: 네트워크가 필요한 Action은 `SKIPPED(offline)`으로 표시한다. 캐시된 도구(이미 PATH에 있는 것)만 사용한다.

### 3.2 상태와 멱등성

- `<target>/.kit/state.json`: kit가 쓴 파일 경로와 SHA-256 해시, 프로필. 실행 시각은 넣지 않는다(재실행 시 바이트 동일해야 멱등성 검사가 성립).
- `<target>/.kit/backups/<YYYYmmdd-HHMMSS>/`: 수정 전 원본.
- 재실행 시: 대상 파일 해시 == 기록 해시 == 새 내용 해시 → 건너뜀. 대상 해시 == 기록 해시 ≠ 새 내용 → 갱신(백업 후). 대상 해시 ≠ 기록 해시 → 사용자가 수정한 것 → `CONFLICT`, 덮어쓰지 않음.
- state.json에 기록이 없는데 같은 경로에 파일이 있음 → 내용이 같으면 채택(adopt), 다르면 `CONFLICT`.

### 3.3 AGENTS.md 병합

- kit 내용은 `<!-- hackathon-kit:begin -->` … `<!-- hackathon-kit:end -->` 보호 구간 안에만 쓴다.
- 대상에 AGENTS.md 없음 → 보호 구간만 담은 파일 생성.
- 있고 보호 구간 없음 → 백업 후 파일 끝에 보호 구간 추가. 기존 내용은 바이트 단위로 보존.
- 있고 보호 구간 있음 → 구간 내부만 교체. 구간 내부가 state.json 해시와 다르면 `CONFLICT`.
- 보호 구간 마커가 짝이 맞지 않으면 `CONFLICT`.

### 3.4 MCP 등록

- 대상의 `.codex/config.toml`에만 `[mcp_servers.<name>]` 테이블을 추가한다. 전역 `~/.codex/config.toml`은 읽기만 한다.
- 표준 라이브러리에 TOML 쓰기기가 없으므로 kit 테이블은 `# hackathon-kit:begin` … `# hackathon-kit:end` 주석 구간에 텍스트로 쓴다. 쓰기 전후 `tomllib`(3.11+)로 파싱해 유효성과 기존 키 보존을 확인한다. 3.9~3.10에서는 파싱 검증을 `UNVERIFIED`로 보고한다.
- 같은 이름의 서버가 구간 밖에 이미 있으면 `CONFLICT`, 수정하지 않는다.
- 보고에 "신뢰된 프로젝트가 아니면 Codex가 이 파일을 로드하지 않을 수 있음"을 표시한다.

## 4. Skill 설계

### 4.1 공통 형식

- frontmatter는 `name`, `description`만. description은 "Use when …"으로 시작하고 "Do NOT use when …"을 포함하며 약 300자. 6개 합계 2,000자 이하.
- 본문은 150줄 이하 절차 체크리스트.
- 언어별 명령(테스트 러너, 린터, 프로파일러)은 `.agents/skills/_shared/` 같은 공유 폴더 대신 각 Skill의 `references/languages.md`에 둔다. Codex는 Skill 폴더 단위로 읽으므로 공유 폴더를 가정하지 않는다. 중복은 Python 기본 + C++/Java/JS 짧은 표로 제한한다. 실행 명령이 필요한 4개(tdd-automator, algorithm-optimizer, submission-validator, benchmark)만 이 파일을 가진다. task-router와 implementation-review는 명령을 실행하지 않으므로 두지 않는다.
- 외부 전송 금지, 서술형 단계 지원 금지, 제출 버튼·브라우저 조작 금지는 AGENTS.md에 한 번만 둔다.
- 각 Skill은 `examples/`에 공개·가상 모의 과제 1건을 둔다.

### 4.2 Skill 목록

| Skill | 호출 | 핵심 절차 | 산출물 |
|---|---|---|---|
| task-router | 암묵 허용 (과제 시작) | 요구사항·제약·I/O 형식·평가 기준 추출 → 유형 분류(algorithm / data / web-api / output-format / debugging / other) → 최소 Skill 선택 | `TASK_BRIEF.md`: 목표, 확정 사실/가정, 위험, 선택 Skill과 사유 |
| tdd-automator | 암묵 허용 (핵심 로직 구현 전) | 문제 정의에서 경계값 선택 → 실패 테스트 → 구현 → 통과 확인. 실행 불가 시 사유 기록 | 테스트 파일, 실행 결과 |
| algorithm-optimizer | 암묵 허용 (큰 입력·시간 제한) | 입력 상한에서 허용 복잡도 역산 → 병목 → 대안 비교 → 테스트 재실행 | 전후 복잡도·측정치 |
| submission-validator | 암묵 허용 (제출 전) | 요구사항 체크리스트 대조, 파일명·경로·형식, 디버그 출력, 테스트·린트 실행, 자동/수동 확인 분리 | 근거 명령이 붙은 검증 표 |
| implementation-review | **명시 호출만** | 핵심 분기, 자료구조 선택, 정당성, 복잡도, 한계 요약. 주석은 핵심 함수에만 | 요약 |
| benchmark | **명시 호출만** | 합성 입력 → timeit / cProfile / tracemalloc → 동일 조건 전후 비교, 노이즈 명시 | 측정표 |

명시 호출 전용 Skill은 `agents/openai.yaml`에 `policy.allow_implicit_invocation: false`를 둔다.

`TASK_BRIEF.md`는 긴 과제 중 컨텍스트가 길어져도 요구사항을 다시 읽을 수 있게 하는 용도이며, 대상 작업 공간 안에만 쓴다.

### 4.3 AGENTS.md

지시서 7절의 템플릿을 그대로 쓰고, 다음 두 줄만 추가한다.

- `Start non-trivial tasks with the task-router skill; skip it for one-line fixes.`
- `Write TASK_BRIEF.md in the workspace only; never outside it.`

## 5. 상태 판정

### 5.1 항목별 3축

각 항목은 `installed`, `registered`, `verified`를 따로 보고한다. `verified` ∈ {`PASS`, `FAIL`, `UNVERIFIED`, `SKIPPED`}.

### 5.2 필수 / 선택 항목

- 필수: 대상 경로 쓰기 가능, AGENTS.md 보호 구간 존재, core Skill 4개(task-router, tdd-automator, algorithm-optimizer, submission-validator) 정적 검증 통과.
- 선택: 보조 Skill 2개, 프로필 도구, MCP, `.codex/config.toml` 파싱 검증.

### 5.3 최종 상태

- `BLOCKED`: 필수 항목 FAIL, 필수 항목에 미해결 CONFLICT, 또는 audit가 금지 설정 탐지.
- `PARTIAL`: 필수 통과, 선택 항목 FAIL·미지원·CONFLICT 존재, 또는 셸 대체 경로로 실행됨.
- `READY`: 필수 항목 모두 PASS. Skill의 Codex 로드가 `UNVERIFIED`여도 READY이며, 보고에 `Codex load: UNVERIFIED (open Codex and run /skills)`를 별도 표시한다.

### 5.4 종료 코드

| 코드 | 의미 |
|---|---|
| 0 | READY (dry-run 정상 완료 포함) |
| 1 | PARTIAL |
| 2 | BLOCKED |
| 64 | 잘못된 인수 |
| 65 | 대상 경로 없음·접근 불가 |

### 5.5 보고 형식

지시서 2.3절 형식을 따르고 `Codex load:` 줄을 추가한다. `Next action`은 1~3개.

## 6. 프로필

`profiles/<name>.json`, `extends`로 상속.

| 프로필 | 내용 |
|---|---|
| core | AGENTS.md, Skill 6개. 도구 설치 없음. 기본값 |
| python | core + pytest, ruff. PATH에 있으면 설치 생략. 없으면 `uv tool install <pkg>==<ver>` → `python -m pip install --user <pkg>==<ver>` |
| data | python + numpy/pandas는 **설치하지 않고** 설치 명령만 안내 |
| web | core + 대상의 `package.json`/lockfile 탐지, node 버전과 `engines` 일치 검사. 설치 없음 |
| full | 모든 후보 점검(설치 가능 여부 보고). 사전 개발 전용, 비활성 MCP는 계속 비활성 |

재시도는 최대 1회. 관리자 권한을 요구하지 않는다.

## 7. MCP

- `mcp/manifest.json`: 후보별 패키지명, 고정 버전, 라이선스, 전송 방식, 네트워크 송신 여부, 파일 접근 범위, `enabled_by_default`, 비활성 사유.
- `sequential-thinking`(`@modelcontextprotocol/server-sequential-thinking`, 구현 시점에 버전 확인·고정)만 기본 활성. stdio, `npx -y <pkg>@<ver>`.
- `fetch`, `git`, `filesystem`은 `enabled_by_default: false`와 사유만 기록하고 등록하지 않는다.
- `mcp/allowlist.json`: 허용 서버 이름, 허용 명령(`npx`, `uvx`), 금지 키(`url`, `bearer_token_env_var`), 금지 env 이름 패턴.
- 검증: (1) stdio로 서버 실행 → JSON-RPC `initialize` → `tools/list`에 도구 1개 이상 → PASS. (2) codex 실행 파일이 있으면 대상 디렉터리에서 `codex mcp list --json`에 이름이 나타나는지 확인. 없거나 신뢰되지 않은 프로젝트라 안 보이면 `UNVERIFIED`.
- `--no-mcp`/`--offline`이면 MCP는 `SKIPPED`이고 상태 판정에서 선택 항목 실패로 치지 않는다.

## 8. 보안 감사

- manifest·allowlist에 없는 MCP 서버 → 거부.
- 설정에 `url` 키, http(s) 원격 엔드포인트, `*_API_KEY`/`*_TOKEN`/`*_SECRET` 성격의 env 요구 → 거부.
- 저장소 자체 코드 스캔(테스트로 실행): `git push`, `curl … | sh`, `Invoke-WebRequest … | iex`, 텔레메트리 엔드포인트 패턴이 있으면 실패. 문서·테스트 픽스처의 의도적 예시는 경로로 제외한다.
- 모든 쓰기 경로는 `resolve()` 후 대상 하위인지 확인. `../`·심볼릭 링크 탈출 거부.
- 로그: 환경 변수는 이름만 기록. 토큰 형태 문자열(`sk-…`, `ghp_…`, 긴 hex/base64)은 `***`로 마스킹.
- 이 검사들은 위험을 줄이는 장치이지 완전한 보안 장치가 아님을 `docs/SECURITY.md`에 명시한다.

## 9. 셸 진입점

- `bootstrap.sh`(bash 3.2+ 호환), `bootstrap.ps1`(Windows PowerShell 5.1+ 호환). 같은 옵션, 같은 종료 코드.
- Python 탐색 순서: `$KIT_PYTHON` → `python3` → `python` → (Windows) `py -3`. 버전이 3.9 미만이거나 Windows Store 별칭 스텁이면 부재로 간주.
- Python 부재 시 최소 배치: `<target>/AGENTS.md`가 없으면 보호 구간으로 감싼 kit AGENTS.md 생성, 이미 보호 구간이 있으면 건너뜀, 보호 구간 없는 기존 파일이면 CONFLICT. `<target>/.agents/skills/<name>/`이 없으면 복사, 있으면 건너뜀. MCP·도구 설치는 하지 않음. AGENTS.md CONFLICT면 5.3 규칙대로 BLOCKED(2), 그 외에는 PARTIAL(1). 수동 확인 안내 출력.
- 셸이 Python에 넘길 때는 `PYTHONPATH` 대신 저장소 루트의 `run_kit.py`를 `python -I`로 실행한다. Git Bash가 `:` 구분 경로 목록을 Windows Python에 넘길 때 깨지는 문제를 피하고, 현재 디렉터리의 모듈이 끼어드는 것도 막는다.
- `--dry-run`은 셸 경로에서도 지원한다.

## 10. 테스트

- 프레임워크: pytest (개발 의존성). kit 자체는 런타임 의존성 없음.
- 격리: `tmp_path` 작업 공간, `HOME`/`USERPROFILE`을 tmp로 교체, `PATH` 앞에 가짜 `codex`/`npx`/`uv` 실행 파일(Python 스크립트 + Windows용 `.cmd` 래퍼) 배치. 가짜 실행 파일은 호출 인수를 파일에 기록하고 시나리오 환경 변수에 따라 성공·실패 출력.
- 네트워크 차단: `--offline` 테스트에서 `socket.socket.connect`를 막는 fixture 사용 + 가짜 실행 파일 호출 기록에 네트워크 동작 없음 확인.

| 테스트 파일 | 다루는 시나리오 |
|---|---|
| test_preflight.py | 도구 탐지, 버전 파싱, 쓰기 불가 대상, Store 별칭 스텁 |
| test_profiles.py | 상속, 잘못된 프로필, `--help`, 잘못된 인수 종료 코드 |
| test_idempotency.py | 2회 실행 후 트리 해시 동일, dry-run 무변경 |
| test_registration.py | 기존 AGENTS.md 보존, 보호 구간 갱신, 사용자 수정 → CONFLICT, config.toml 병합·기존 키 보존 |
| test_security.py | 원격 MCP 거부, 경로 순회 거부, 로그 마스킹, 저장소 금지 패턴 스캔 |
| test_failure_recovery.py | MCP 실패 → PARTIAL, 도구 설치 실패, 중간 실패 후 재실행 일관성, offline |
| test_entrypoints.py | sh/ps1의 `--help`, 잘못된 인수, `KIT_PYTHON` 부재 → 셸 경로 |
| test_skills.py | frontmatter 파싱, 이름·폴더 일치, description 길이·"Do NOT use" 포함, 합계 길이 |

- 정적 분석: `ruff check`, `ruff format --check`(kit/, tests/), `shellcheck bootstrap.sh`. PSScriptAnalyzer는 설치돼 있으면 실행, 없으면 "미실행"으로 보고.
- 수동 통합 1회: 로컬 codex 0.164.0으로 `codex mcp list --json`, TUI `/skills` 확인 → `docs/TEST_REPORT.md`에 기록.
- 예시 로그: 정상 설치, 실패, 재실행, 오프라인, 설정 충돌 각 1건을 `docs/examples/`에 저장(마스킹 후).

## 11. 일정

| 날짜 | 작업 | 완료 기준 |
|---|---|---|
| 10/28 | 설계 → 계획 → Phase 1: AGENTS.md, Skill 6개, core 프로필, preflight, dry-run | `core --dry-run`이 대상 무변경으로 예상 작업 출력 |
| 10/29 | Phase 2: register·백업·멱등, sh/ps1 진입점, 셸 대체 경로, 테스트 | **필수선**. 모의 작업 공간 2회 실행 후 동일 |
| 10/30 | Phase 3~5: python 프로필, sequential-thinking MCP, audit, data/web/full, 문서. 저녁: 기능 동결, 깨끗한 환경에서 one-liner 재현 | 지시서 10절 체크리스트, TEST_REPORT.md |
| 10/31 | 변경 없음 | — |

일정이 밀리면 10/30 항목은 뒤에서부터(full → web → data → audit 세부) 잘라내고 ASSUMPTIONS.md에 미구현으로 기록한다.

## 12. 문서 전달물

`README.md`(첫머리에 "Claude Code 사전 개발 전용 / 시험 중 사용 불가", OS별 one-liner, 옵션, 종료 코드, 예상 출력, 실패 대응), `docs/ARCHITECTURE.md`, `docs/ASSUMPTIONS.md`, `docs/SECURITY.md`, `docs/COMPATIBILITY.md`, `docs/RULES_CHECKLIST.md`, `docs/TROUBLESHOOTING.md`, `docs/TEST_REPORT.md`, 공개 전 점검 체크리스트(README 하단).

`docs/RULES_CHECKLIST.md`에는 **사전 체험 15분 체크리스트**를 둔다. 각 항목마다 "안 되면 → 대체 경로"를 함께 적는다.

1. 셸 종류 확인 (bash / PowerShell / 없음)
2. `git`, `python`, `node` 존재
3. 공개 GitHub 접근 가능 여부 (`git clone`만으로 확인, 별도 네트워크 탐지 없음)
4. 스크립트 실행 가능 여부 → 불가 시 `AGENTS.md`와 `.agents/` 폴더를 작업 공간에 수동 복사
5. Codex에서 `/skills`로 kit Skill 표시 여부
6. `/mcp` 또는 `codex mcp list`로 MCP 표시 여부 → 안 보이면 MCP 없이 진행
7. 설치한 파일이 세션 재시작 후 유지되는지

감독·보안 기능을 탐지하거나 시험하는 항목은 넣지 않는다.

## 13. 하지 않는 것

- 시험 중 GitHub push, 원격 동기화, 릴리스. 키트 코드에도 그런 자동화를 넣지 않는다. (키트 저장소 자체는 시험 전에 GitHub에 올려 두고, 시험 환경에서는 공개 저장소를 `git clone`한 뒤 한 줄 명령으로 설치한다.)
- 사용자 전역 `~/.codex`, `~/.agents` 수정.
- 외부 모델·API 연결, Computer Use, 브라우저·감독 앱 조작, 서술형 답안 자동화.
- 실제 시험 콘텐츠 사용·추측·수집.
- `curl | bash` 방식 설치.
