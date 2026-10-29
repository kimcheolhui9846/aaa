# 테스트 보고서 (계획 1)

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
