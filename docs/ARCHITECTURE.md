# 아키텍처

## 왜 `kit/`인가

지시서는 `scripts/*.py`를 가정했지만 이 저장소는 `kit/` 패키지를 쓴다. import와 테스트가 단순해지기 때문이다. 대응은 1:1이다.

- `scripts/install.py` → `kit/tools.py`
- `scripts/audit.py` → `kit/audit.py`

`kit/`는 Python 표준 라이브러리만 쓴다(런타임 의존성 없음). 개발 의존성(pytest, ruff)은 `uv.lock`에 있다.

## 실행 흐름

```text
bootstrap.sh / bootstrap.ps1  ->  run_kit.py  ->  kit.app.run
```

셸 스크립트는 Python 3.9+를 찾아 `python -I run_kit.py <인수>`로 넘긴다. `run_kit.py`가 저장소 루트를 `sys.path`에 넣는다(`PYTHONPATH`를 쓰지 않는다). Python이 없으면 셸 전용 모드로 `AGENTS.md`와 Skill만 복사한다(프로필과 무관하게 도구·MCP 없음, 종료 코드 1).

`kit.app.run`의 순서:

1. 인수 파싱과 프로필 로드, 대상이 키트 폴더 자신이면 거부(종료 코드 65)
2. preflight (`preflight.py`): OS, 셸, 쓰기 가능 여부, 도구 버전
3. plan (`plan.py`): 파일별로 create / update / append / conflict / unchanged 결정. `--dry-run`이면 여기서 출력하고 종료
4. apply (`register.py`): 백업 후 원자적 쓰기, 상태 저장
5. tools (`tools.py`): 프로필 도구 확인과 설치
6. verify (`verify.py`, `mcpconfig.verify_config`): 대상의 실제 내용 검사
7. audit (`audit.py`): `.codex/config.toml`을 allowlist와 대조
8. web check (`webcheck.py`): `node-project` 도구가 있는 프로필만
9. MCP check (`mcpcheck.py`): stdio 핸드셰이크와 `codex mcp list --json`
10. report와 로그 (`report.py`, `logs.py`)

`--verify-only`는 apply와 설치를 건너뛴다. 예상치 못한 예외는 `kit.app.main`이 잡아 `BLOCKED`로 끝낸다.

## 모듈

| 모듈 | 역할 |
|---|---|
| `model.py` | 항목 결과(`ItemResult`), 판정 문자열, 종료 코드, 예외 |
| `cli.py` | 인수 → `Options`. 오류는 종료하지 않고 예외로 올린다 |
| `profiles.py` | `profiles/*.json` 로드, `extends` 상속, 검증 |
| `preflight.py` | OS·셸·도구(`git uv node npx codex python`) 탐지 |
| `fsops.py` | `safe_path`, SHA-256, `.kit/state.json`, 백업 |
| `agentsmd.py` | 보호 구간 렌더링·추출·병합(마커를 인수로 받는다) |
| `skills.py` | `SKILL.md` frontmatter 파싱과 검증 |
| `plan.py` | 변경 계획과 계획 출력 |
| `register.py` | 계획 적용(원자적 쓰기, 백업, 실패해도 상태 저장) |
| `verify.py` | AGENTS.md, Skill, 쓰기 가능 여부 검사 |
| `mcpconfig.py` | manifest·allowlist 로드, 설정 블록 렌더링, 병합 검사, 설정 검증 |
| `audit.py` | 설정을 allowlist와 대조 |
| `tools.py` | 도구 설치 계획과 실행(`uv tool install` → `pip install --user`) |
| `webcheck.py` | `package.json`, lockfile, `engines.node` 검사 |
| `mcpcheck.py` | MCP 서버 핸드셰이크, `codex mcp list --json` 조회 |
| `report.py` | 최종 상태 판정, 다음 행동, 보고서 출력 |
| `logs.py` | 비밀 마스킹과 `.kit/logs/` 기록 |
| `app.py` | 위 단계를 엮는 `run`과 `main` |

## 상태와 멱등성

- `<target>/.kit/state.json`에 키트가 쓴 파일의 경로와 해시, 프로필을 기록한다. 실행 시각은 넣지 않는다.
- 대상 해시가 새 내용과 같으면 건너뛴다(`unchanged`).
- 대상 해시가 기록 해시와 같고 새 내용과 다르면 백업 후 갱신한다(`update`).
- 대상 해시가 기록 해시와 다르면 사용자가 고친 것이므로 `CONFLICT`로 두고 쓰지 않는다.
- 기록이 없는데 같은 경로에 파일이 있으면, 내용이 같으면 채택하고 다르면 `CONFLICT`다.
- 수정 전 원본은 `.kit/backups/<YYYYmmdd-HHMMSS>/`에 남는다.

## 마커 두 쌍

| 파일 | 시작 | 끝 |
|---|---|---|
| `AGENTS.md` | `<!-- hackathon-kit:begin -->` | `<!-- hackathon-kit:end -->` |
| `.codex/config.toml` | `# hackathon-kit:begin` | `# hackathon-kit:end` |

키트는 구간 안만 고친다. 마커가 짝이 맞지 않거나 중복되면 `CONFLICT`다. `config.toml`에서 같은 이름의 서버가 구간 밖에 있어도 `CONFLICT`이며 파일은 그대로 둔다.

## 종료 코드

| 코드 | 의미 |
|---|---|
| 0 | READY (dry-run 완료 포함) |
| 1 | PARTIAL |
| 2 | BLOCKED |
| 64 | 잘못된 인수 |
| 65 | 대상 디렉터리 없음 또는 키트 폴더 자신 |

필수 항목의 FAIL·CONFLICT는 `BLOCKED`, 선택 항목의 FAIL·CONFLICT는 `PARTIAL`이다. `UNVERIFIED`와 `SKIPPED`는 상태를 낮추지 않는다.
