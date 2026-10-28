# 문제 해결

따옴표 안의 문구는 키트가 실제로 출력하는 메시지다. 보고서의 `Items:` 줄은 `판정 필수/선택 항목 (상세)` 형식이다. 수정한 뒤에는 같은 명령을 다시 실행하면 된다(멱등).

## CONFLICT

키트는 `CONFLICT` 파일을 고치지 않는다. 사용자가 판단해야 한다. 필수 항목이면 `BLOCKED`(종료 코드 2), 선택 항목이면 `PARTIAL`(1)이다.

| 항목 | 메시지 | 의미와 조치 |
|---|---|---|
| `AGENTS.md` | `kit block was edited outside the kit` | 보호 구간 안을 직접 고쳤다. 키트의 `AGENTS.md`와 비교해 되돌리거나 구간 밖으로 옮긴 뒤 재실행 |
| `AGENTS.md`, `mcp-config` | `expected exactly one begin and one end marker` | 마커가 없거나 중복이다. 짝을 맞춘 뒤 재실행 |
| `AGENTS.md`, `mcp-config` | `end marker appears before begin marker` | 마커 순서가 뒤바뀌었다. 바로잡고 재실행 |
| `skill:<이름>` | `differs from the kit copy and was not written by the kit` | Skill 파일을 고쳤거나 기존 파일이 있다. 키트 복사본(`.agents/skills/<이름>/`)과 비교해 유지하거나 삭제 후 재실행 |
| `mcp-config` | `MCP server 'sequential-thinking' is already defined outside the kit block` | 같은 이름의 서버가 구간 밖에 이미 있다. 이름을 바꾸거나 직접 정리 |
| `mcp-config` | `merging would change existing config.toml settings` | 병합하면 기존 설정이 바뀐다. 설정을 확인 |
| `mcp-config` | `merged config.toml would not be valid TOML: ...` | 기존 `config.toml`의 TOML이 깨져 있다. 고친 뒤 재실행 |
| 공통 | `exists but is not a regular file` | 같은 경로가 디렉터리 등이다. 옮기거나 삭제 |

## security audit FAIL

`.codex/config.toml`이 `mcp/allowlist.json`과 어긋난다. 필수 항목이므로 `BLOCKED`다. 메시지 예:

- `<서버>: not in mcp/allowlist.json`
- `<서버>: forbidden key 'url' (remote transport)`
- `<서버>: command '...' is not allowed`
- `<서버>: remote endpoint '...'`
- `<서버>: secret-like env '...'`

해당 서버 설정을 `config.toml`에서 지우거나 고친다. 키트가 쓴 구간이 아니면 키트는 건드리지 않았다. 설정이 유효한 TOML이 아니면 `cannot audit: config is not valid TOML (...)`로 `UNVERIFIED`가 된다.

## 도구 설치

| 메시지 | 조치 |
|---|---|
| `tool:* install failed: <마지막 출력 줄>` | `uv tool install`과 `pip install --user`가 모두 실패했다(명령당 1회 재시도). 네트워크나 권한을 확인하거나 `--offline`으로 건너뛰고 직접 설치 |
| `installed with ... but `pytest` is not on PATH; open a new shell or add the scripts folder to PATH` | 설치는 됐지만 PATH에 없다(`UNVERIFIED`). 새 셸을 열거나 스크립트 폴더를 PATH에 추가 |
| `not installed; run without --verify-only to install (...)` | `--verify-only`는 설치하지 않는다. 옵션 없이 실행 |
| `offline; install later with: ...` | `--offline`이라 건너뛰었다(상태를 낮추지 않음) |

## MCP

| 메시지 | 조치 |
|---|---|
| `npx not found; install Node.js or use --no-mcp` | Node.js를 설치하거나 `--no-mcp`로 실행 |
| `no response within 120s` | 첫 실행은 npx가 패키지를 받는다. 네트워크를 확인하고 재시도하거나 `--no-mcp`. Windows에서 node 프로세스가 남으면 작업 관리자에서 종료 |
| `server exited before answering` | 서버가 응답 전에 종료했다. node 버전과 네트워크 확인 |
| `initialize was rejected` | 서버가 `initialize`를 거부했다 |
| `server listed no tools` | `tools/list`가 비었다 |
| `cannot start server: ...` | 실행 파일을 시작하지 못했다 |
| `codex not found; check /mcp in Codex` | `codex-mcp` `UNVERIFIED`. Codex에서 `/mcp` 확인 |
| `not listed by `codex mcp list`; trust this project in Codex, then check /mcp` | `UNVERIFIED`. Codex에서 프로젝트를 신뢰(trust)한 뒤 `/mcp` 확인. Codex는 `.codex/config.toml`을 신뢰된 프로젝트에서만 로드한다 |
| `TOML parse check needs Python 3.11+; ...` | `UNVERIFIED`. Python 3.11+에서는 파싱 검사를 한다. 3.9~3.10에서는 `config audit needs Python 3.11+ (tomllib)`도 나온다 |

MCP가 필요 없으면 `--no-mcp`(항목 `SKIPPED`)를 쓴다. `SKIPPED`는 상태를 낮추지 않는다.

## web 프로필

- `no package.json in target`: 건너뜀(`SKIPPED`).
- `package.json is not valid JSON: ...`: `package.json`을 고친다.
- `node not found; ...`: Node.js를 설치한다.
- `node <버전> does not satisfy engines.node '<범위>'; ...`: node 버전을 맞춘다.
- `cannot evaluate engines.node '<범위>' against <버전>; ...`: 키트가 해석하지 못하는 범위이며 `UNVERIFIED`다. 직접 확인한다.

## 종료 코드 64와 65

| 코드 | 메시지 | 조치 |
|---|---|---|
| 64 | `--dry-run and --verify-only cannot be combined` | 둘 중 하나만 쓴다 |
| 64 | `--target needs a non-empty directory` | 빈 문자열을 주지 않는다 |
| 64 | `unknown profile '<이름>' (available: ...)` | `core`, `data`, `full`, `python`, `web` 중에서 고른다 |
| 65 | `target is not an existing directory: <경로>` | 폴더를 만들거나 경로를 고친다 |
| 65 | `target is the kit folder itself; run from your workspace or pass --target <workspace>` | 작업 공간에서 실행하거나 `--target`을 준다 |

## 셸 전용 모드

Python 3.9+가 없으면 `Mode:         shell-only (no Python 3.9+)`로 실행하고 `Status:       PARTIAL`(종료 코드 1)로 끝난다. `Next action`의 `Install Python 3.9+ and re-run to verify files and enable tools/MCP.`를 따른다. 이 모드는 프로필과 상관없이 `AGENTS.md`와 Skill만 설치한다.

- `AGENTS.md (exists; merging needs Python - add the kit block by hand)`: 기존 `AGENTS.md`에 키트 구간이 없다. 키트 `AGENTS.md`를 구간 마커로 감싸 직접 추가하면 `BLOCKED`가 풀린다.
- `error: --verify-only requires Python 3.9+ (shell-only mode cannot verify)`: 종료 코드 64.
- `.agents/skills/<이름> (exists, not checked)`: 기존 Skill은 검사하지 않고 건너뛴다.
