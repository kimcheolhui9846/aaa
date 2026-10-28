# 가정과 미확인 사항

`UNVERIFIED`는 사전 체험이나 운영 측 확인 전까지 사실로 취급하지 않는다는 뜻이다.

## 시험 환경 (모두 UNVERIFIED)

| 항목 | 상태 | 확인 방법 | 안 될 때 |
|---|---|---|---|
| bash 또는 PowerShell 실행 가능 | UNVERIFIED | 사전 체험에서 터미널 열기 | 파일 수동 복사 |
| git 사용 가능 / 공개 GitHub 접근 | UNVERIFIED | `git clone` 시도 | 키트를 받을 수 없으면 키트 없이 진행 |
| Python 3.9+ 존재 | UNVERIFIED | `python --version` | 셸 모드(PARTIAL)로 진행 |
| 스크립트 자동 설치 허용 | UNVERIFIED | 공지·감독관 확인 | 실행하지 않고 수동 복사 |
| Codex가 `.agents/skills`를 탐색 | UNVERIFIED | Codex에서 `/skills` | `AGENTS.md`만으로 진행 |
| 설치한 파일이 세션 동안 유지 | UNVERIFIED | 재접속 후 파일 확인 | 다시 실행(멱등) |

## 로컬에서 확인한 사실 (2026-10-28, codex-cli 0.165.0)

- Skill 탐색 경로: `$CWD/.agents/skills` ~ 저장소 루트의 `.agents/skills`, `$HOME/.agents/skills`.
- `agents/openai.yaml`의 `policy.allow_implicit_invocation: false`로 명시 호출 전용 Skill을 만들 수 있다.
- `codex debug prompt-input` 출력에는 Skill 목록이 나타나지 않는다. Skill 로드는 비대화형으로 검증할 수 없어 보고서에 `Codex load: UNVERIFIED`로 표시한다.
- 프로젝트 `.codex/config.toml`은 신뢰된 프로젝트에서만 로드된다(계획 2의 MCP에 해당).

## 설계상 가정

- 대상 작업 공간은 Codex를 실행할 디렉터리(또는 그 상위 저장소 루트)다.
- 셸 전용 모드는 심볼릭 링크 차단이 없다. 작업 공간에 미리 심어 둔 `.agents` 심볼릭 링크는 범위 밖이다(Python 모드는 대상 밖 경로 쓰기를 거부한다).
- 텍스트 파일은 UTF-8이다. UTF-8이 아닌 기존 `AGENTS.md`는 CONFLICT로 남긴다.
