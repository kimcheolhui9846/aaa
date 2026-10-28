# 보안

이 검사들은 위험을 줄이는 장치이며 완전한 보안 경계가 아니다.

## 코드가 강제하는 것

- 모든 쓰기는 `safe_path`를 거친다. `resolve()` 후 대상 하위가 아니면(`..`, 절대 경로, 심볼릭 링크 탈출) 거부한다.
- 파일을 바꾸기 전에 원본을 `.kit/backups/<시각>/`에 복사한다. 쓰기는 `.kit-tmp` 임시 파일을 거친 원자적 교체다.
- 전역 설정을 쓰지 않는다. 쓰는 곳은 대상의 `AGENTS.md`, `.agents/skills/`, `.codex/config.toml`, `.kit/`뿐이다.
- MCP는 `mcp/manifest.json`에서 `enabled_by_default`가 참이고 `mcp/allowlist.json`의 `servers`에 있는 것만 등록한다. 지금은 `sequential-thinking` 하나다.
- 감사(`kit/audit.py`)는 `.codex/config.toml`에서 다음을 FAIL로 본다. allowlist에 없는 서버, 금지 키(`url`, `bearer_token_env_var`), 허용 목록(`npx`, `uvx`) 밖의 명령, `http://`·`https://` 원격 엔드포인트, `env`·`env_vars`의 `_API_KEY`·`_TOKEN`·`_SECRET`으로 끝나는 이름(대소문자 무시).
- 로컬 로그(`.kit/logs/`)는 `*_TOKEN=`, `*_API_KEY=` 같은 값, `Bearer` 값, `sk-…`, `ghp_…` 형태를 `***`로 가린다. 환경 변수 값은 기록하지 않는다.
- 저장소 스캔 테스트(`tests/test_security.py`)가 위험 패턴을 찾는다.
- `--offline`이면 도구 설치와 MCP 핸드셰이크를 하지 않는다. 네트워크 접근이 전혀 없다.

## 네트워크 동작과 시점

네트워크는 아래 경우에만 쓰며, 보고서의 `Network:` 줄에 표시한다. `--dry-run`은 설치하지 않고 서버를 시작하지 않는다(`--version` 점검은 실행한다). `--verify-only`는 설치하지 않지만 MCP 핸드셰이크(`npx -y`)는 `--offline`·`--no-mcp`가 아닌 한 실행하며, 이때 네트워크와 대상 밖의 npm 캐시를 쓴다.

| 동작 | 언제 |
|---|---|
| `uv tool install <pkg>==<ver>` | python 프로필, 도구가 PATH에 없고 `uv`가 있을 때 |
| `python -m pip install --user <pkg>==<ver>` | 위가 불가하거나 실패했을 때 |
| `npx -y <pkg>@<ver>` | MCP 핸드셰이크: python, data, web, full 프로필(`--offline`·`--no-mcp`가 아닐 때) |

`core`와 `web` 프로필은 도구를 설치하지 않는다. `data`는 numpy·pandas를 설치하지 않고 명령만 안내한다. `full`은 도구를 설치하지 않지만 `python`을 상속하므로 sequential-thinking 등록과 npx 핸드셰이크는 한다.

## 알려진 한계

- `npx`는 최상위 패키지만 버전을 고정한다. 하위 의존성은 범위 지정에 따라 해석되므로 설치 시점에 달라질 수 있다.
- `uv tool`과 `pip --user`는 대상 밖의 사용자 수준 도구 폴더에 설치한다. 대상 폴더 쓰기 제한은 이 설치에 적용되지 않는다.
- 서버가 stdin 종료를 무시하면 핸드셰이크 뒤에 프로세스가 남을 수 있다(`docs/COMPATIBILITY.md`).
- 감사는 `config.toml`의 정적 검사다. 서버 코드가 실제로 하는 일은 검사하지 않는다.
- manifest의 `sequential-thinking` 네트워크 송신과 파일 접근 항목은 "예상"이며 확인한 사실이 아니다. 라이선스는 2026.8.31에 대해 다시 확인하지 않았다.

## 비활성 MCP 서버

`mcp/manifest.json`에 후보로 기록만 하고 등록하지 않는다.

| 서버 | 사유 |
|---|---|
| `fetch` | fetches arbitrary URLs: can send task data outside the workspace |
| `git` | exposes git operations; remote sync and push are forbidden in the exam |
| `filesystem` | duplicates Codex's own file access and widens the reachable paths |
