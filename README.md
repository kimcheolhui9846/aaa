# hackathon-agent-kit

> **Claude Code 사전 개발 전용 / 시험 중 사용 불가.** 이 저장소는 시험 전에 Claude Code로 개발했다. 시험 중에는 운영 환경이 제공하는 Codex만 사용하며, 이 키트는 Codex가 읽을 `AGENTS.md`와 Skill 파일을 작업 공간에 배치할 뿐 외부 모델이나 네트워크를 호출하지 않는다.

대상 작업 공간에 Codex용 정책 파일(`AGENTS.md`)과 Skill 6개(`.agents/skills/`)를 안전하게 설치하고, 설치 결과를 READY / PARTIAL / BLOCKED로 보고한다.

## 한 줄 설치

`<USER>`와 `<REPO>`를 본인 GitHub 주소로 바꾼다. 복제와 실행은 분리돼 있다(`curl | bash` 방식 아님).

bash (Linux/macOS/Git Bash):

```bash
git clone --depth 1 https://github.com/<USER>/<REPO>.git && bash <REPO>/bootstrap.sh --target .
```

Windows PowerShell:

```powershell
git clone --depth 1 https://github.com/<USER>/<REPO>.git; if ($LASTEXITCODE -eq 0) { & .\<REPO>\bootstrap.ps1 --target . }
```

실행 정책 때문에 `.ps1`이 막히면 스크립트를 우회하지 말고 아래 "스크립트를 실행할 수 없을 때"를 따른다.

## 옵션

| 옵션 | 의미 |
|---|---|
| `--profile core` | 기본값. AGENTS.md와 Skill 6개만 설치(도구·MCP 없음). 다른 프로필은 계획 2에서 추가 |
| `--target <dir>` | 설치 대상 작업 공간(기본: 현재 디렉터리) |
| `--dry-run` | 아무것도 쓰지 않고 계획만 출력 |
| `--verify-only` | 설치 없이 현재 상태만 검사(로그만 기록) |
| `--offline` | 네트워크를 쓰지 않음(core는 원래 쓰지 않음) |
| `--no-mcp` | MCP를 건너뜀 |
| `--verbose` | 파일·항목별 상세 출력 |
| `--help` | 도움말 |

## 종료 코드

| 코드 | 상태 | 의미 |
|---|---|---|
| 0 | READY | 필수 항목 모두 검증(또는 dry-run 완료) |
| 1 | PARTIAL | 필수 항목은 정상, 선택 항목 일부 실패 또는 Python 없이 셸 모드로 실행 |
| 2 | BLOCKED | 필수 항목 실패 또는 사용자 판단이 필요한 충돌. 셸 모드에서 파일 쓰기에 실패한 경우도 포함 |
| 64 | - | 잘못된 인수 |
| 65 | - | 대상 디렉터리가 없거나 디렉터리가 아님 |

## 예상 출력

```text
Environment:  Windows 11 AMD64, shell=powershell, python 3.12.10
Tools:        git OK, uv OK, node OK, npx OK, codex OK, python OK
Target:       D:\work\task
Profile:      core
AGENTS.md:    INSTALLED
Skills:       6 expected / 6 verified
Codex load:   UNVERIFIED (open Codex and run /skills)
MCP:          none in profile 'core'
Network:      not used
Status:       READY
Next action:
  - Open Codex in D:\work\task and run /skills to confirm the kit skills load.
```

`Codex load: UNVERIFIED`는 정상이다. Codex가 Skill을 실제로 읽었는지는 Codex 안에서 `/skills`로만 확인할 수 있다.

## 안전 장치

- 기존 `AGENTS.md`는 덮어쓰지 않는다. 키트 내용은 `<!-- hackathon-kit:begin -->` … `<!-- hackathon-kit:end -->` 구간에만 쓰고, 수정 전 원본을 `.kit/backups/<시각>/`에 남긴다.
- 키트 구간 안의 줄바꿈이 CRLF여도 비교 전에 정규화한다. 편집기나 git `autocrlf`가 줄바꿈을 바꿔도 충돌로 보지 않는다.
- 사용자가 고친 파일은 `CONFLICT`로 보고하고 건드리지 않는다. `AGENTS.md`가 디렉터리이거나 읽을 수 없는 파일인 경우도 `CONFLICT`로 보고한다.
- 같은 명령을 다시 실행해도 결과가 같다(멱등). 중간에 실패해도 다시 실행하면 이어서 맞춰진다.
- 대상 디렉터리 밖에는 쓰지 않으며 `~/.codex` 같은 전역 설정은 건드리지 않는다.
- 로그는 대상의 `.kit/logs/`에만 남고 토큰 형태 문자열은 가려진다. `GITHUB_TOKEN=`, `OPENAI_API_KEY=`처럼 접두어가 붙은 이름과 `Bearer` 값도 가린다.
- Python이 없을 때의 셸 전용 모드는 파일을 `.kit-tmp` 임시 파일에 쓴 뒤 제자리로 옮긴다. 쓰기에 실패하면 `Status: BLOCKED`(종료 코드 2)로 끝난다.

## 스크립트를 실행할 수 없을 때

키트 폴더의 `AGENTS.md` 내용과 `.agents/` 폴더를 작업 공간 루트에 그대로 복사하면 된다. 그다음 Codex에서 `/skills`로 확인한다.

## 개발

```bash
uv sync
uv run pytest -q
uv run ruff check . && uv run ruff format --check .
shellcheck bootstrap.sh
```

## 공개 전 점검

- [ ] `LICENSE`(MIT) 저자·연도 확인
- [ ] README의 `<USER>/<REPO>`를 실제 주소로 교체
- [ ] 저장소에 토큰·개인 경로·시험 관련 비공개 자료가 없는지 확인
- [ ] `docs/TEST_REPORT.md`가 최신인지 확인
