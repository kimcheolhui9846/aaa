# 호환성

## 지원 범위

| 항목 | 요구 | 비고 |
|---|---|---|
| Python | 3.9+ | 없으면 셸 전용 모드(아래) |
| TOML 파싱, 설정 감사 | Python 3.11+ (`tomllib`) | 3.9~3.10에서는 줄 단위 검사로 위험 항목을 FAIL로 잡고, 못 찾으면 `UNVERIFIED` |
| bash | 3.2+ | `bootstrap.sh` |
| PowerShell | Windows PowerShell 5.1+ | `bootstrap.ps1` |
| Node/npx | MCP에만 필요 | 없으면 MCP 항목이 FAIL(선택), 나머지는 정상 |
| Codex | codex-cli 0.165.0에서 확인 | `codex mcp list --json` 형식 |

Python 탐색 순서는 `$KIT_PYTHON`, `python3`, `python`, (Windows) `py -3`이다. `py -3`은 `bootstrap.ps1`만 시도한다. 3.9 미만이면 없는 것으로 본다.

## Windows의 bash

Git Bash의 `bash`와 WSL의 `bash`는 다르다. `bash`가 어느 쪽으로 잡히는지에 따라 보이는 경로와 도구가 달라질 수 있다. Windows에서는 PowerShell 진입점(`bootstrap.ps1`) 또는 Git Bash를 쓴다. 로컬에서는 Git Bash로 확인했다(`docs/TEST_REPORT.md`).

Windows에서 MCP 점검은 `npx.cmd`(cmd.exe → node)를 시작한다. 서버가 stdin 종료를 무시하면 점검 뒤에 node 프로세스가 남을 수 있다. 작업 관리자에서 직접 종료한다. 핸드셰이크는 최대 120초 기다리고, 종료 시 5초 유예를 둔다.

## MCP 버전 선택

`@modelcontextprotocol/server-sequential-thinking`을 `2026.8.31`로 고정했다. 2.0.0(2026-10-19)은 node 24 이상이 필요하고, 2026.8.31은 `engines`를 선언하지 않아 오래된 시험 환경에서도 시작할 가능성이 높다.

## Codex 신뢰

Codex는 `.codex/config.toml`을 신뢰된 프로젝트에서만 로드한다. 신뢰하지 않으면 MCP가 보이지 않으며 키트는 `codex-mcp:sequential-thinking`을 `UNVERIFIED`로 보고한다. 이는 실패가 아니다. 프로젝트를 신뢰한 뒤 Codex에서 `/mcp`로 확인한다.

`codex mcp list --json`은 JSON 배열(각 원소에 `name`)을 출력하며, 키트는 대상 디렉터리에서 이를 실행해 서버 이름을 찾는다.

## 셸 전용 모드

Python 3.9+가 없으면 어떤 프로필을 고르든 `AGENTS.md`와 Skill만 설치한다. 도구 설치, MCP, 검증, 로그, 백업은 없다. 종료 코드는 1(`PARTIAL`)이다. 자세한 한계는 `README.md`의 "셸 전용 모드의 한계"를 본다.
