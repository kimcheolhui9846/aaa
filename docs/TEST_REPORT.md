# 테스트 보고서

## 계획 1

실행일: 2026-10-28, 환경: Windows 11 AMD64, Python 3.12.10, codex-cli 0.165.0, shellcheck 0.11.0

| 명령 | 결과 | 근거 |
|---|---|---|
| `uv run pytest -q` | PASS | `158 passed, 1 skipped in 25.22s` |
| `uv run ruff check .` | PASS | `All checks passed!` |
| `uv run ruff format --check .` | PASS | `50 files already formatted` |
| `shellcheck bootstrap.sh` | PASS | 출력 없음, 종료 코드 0 |
| PSScriptAnalyzer | 미실행 | `PSScriptAnalyzer not installed - not run` |
| one-liner (PowerShell, clean clone) | PASS | `git clone --depth 1 --branch feat/bootstrap-kit file:///D:/aaa/aaa kit` 후 `bootstrap.ps1 --target .` 첫 실행과 재실행 모두 `Status:       READY`, `exit=0` |
| one-liner (Git Bash) | PASS | `C:\Program Files\Git\bin\bash.exe`로 `bash kit/bootstrap.sh --target .` 실행, 기존 설치 상태와 빈 디렉터리 두 대상 모두 `Status:       READY`, exit 0 |
| Codex `/skills` | UNVERIFIED | 사용자 확인 대기 (Codex TUI에서 /skills) |

## 건너뛴 테스트와 이유
- `tests/test_fsops.py:31` 심볼릭 링크 탈출 테스트: `symlinks not permitted on this system` (Windows에서 심볼릭 링크 권한 없음)

## 미검증
- 시험 환경(Cofa) 전체: docs/ASSUMPTIONS.md 참고
- Codex가 Skill 6개를 실제로 로드하는지, `implementation-review`와 `benchmark`가 명시 호출 전용으로 표시되는지: 사용자의 대화형 확인 필요
- PSScriptAnalyzer가 설치되지 않아 `bootstrap.ps1` 정적 분석은 실행하지 못했다

# 계획 2 (프로필, MCP, 감사)

실행일: 2026-10-28, 환경: Windows 11 AMD64, Python 3.12.10

| 명령 | 결과 | 근거 |
|---|---|---|
| `uv run pytest -q` | PASS | `300 passed, 1 skipped in 36.21s` |
| `uv run ruff check .` | PASS | `All checks passed!` |
| `uv run ruff format --check .` | PASS | `49 files already formatted` |
| `uv run python devtools/make_examples.py` | PASS | `docs/examples/{install,rerun,failure,offline,conflict}.log` 5개 생성. 네트워크 미사용, 로컬 경로는 `<target>`으로 치환 |
| 실제 npx로 sequential-thinking 핸드셰이크 | UNVERIFIED | `bootstrap.ps1 --profile python --target <빈 폴더>`로 사용자가 확인 |

## 예시 로그 판정

| 로그 | 기대 | 결과 |
|---|---|---|
| `install.log` | READY, 종료 코드 0 | 일치 |
| `rerun.log` | READY, CREATE 없음 | 일치 |
| `failure.log` | BLOCKED, 종료 코드 2 | 일치 |
| `offline.log` | `Network:      not used (--offline)`, MCP `SKIPPED` | 일치 |
| `conflict.log` | `skill:benchmark` CONFLICT, PARTIAL, 종료 코드 1 | 일치 |

## 미검증 (계획 2)

- 실제 `npx`로 한 MCP 핸드셰이크(위 표). 테스트는 로컬 가짜 서버만 쓴다.
- 기존 건너뜀 1건은 Windows 심볼릭 링크 권한 때문이다(계획 1과 동일).
