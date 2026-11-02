# AI Company M0 PoC 키트 v0.3 — 오간마음 저장소용

**오늘의 성공 기준**
> 최초 접수 이후 추가 수동 명령 없이 로컬 경로가 봇 PR 생성과 필수 CI(`analyze-and-test`, `protected-paths`) 통과까지 도착한다. 승인 직전에 SHA·최신 CI·보호 경로를 다시 확인하고, 사람이 판단 이유를 기록한다. 실패·누락·skipped·출처 불명 체크는 성공으로 기록되지 않는다.
>
> Routine은 비교 실험이다. Routine이 성공해야 M0가 성공하는 조건은 없다.

**실행 순서**: ① 정책·회고 → ② GitHub 설정 → ③ **GitHub 연결만 먼저 확인 (Claude 실행 없음)** → ④ 인수 조건 1개 → ⑤ 로컬 경로 `run` 완주 → ⑥ 별도 작업으로 Ctrl+C 중단 실험 → ⑦ 시간이 남으면 Routine 비교

③과 ⑤의 증거는 `experiments.md`에서 **따로** 기록한다.

## 용어 — 서로 다른 상태다
| 상태 | 의미 | 누가 |
|---|---|---|
| `AGENT_DONE` | Claude가 성공 결과로 끝나고 커밋이 있음. **완료 아님** | 디스패처 |
| `VERIFIED` | 필수 체크 2개가 그 PR head 커밋에서 둘 다 success | 디스패처 |
| `HUMAN_APPROVED` | 내가 이유와 SHA를 남기고 승인 의사를 기록함 | 나 (`decide`) |
| GitHub 리뷰 승인 | GitHub에서 PR을 Approve | 나 (GitHub에서 따로) |
| 머지 | main에 반영 | 나 (GitHub에서 따로) |
| 배포 | 스토어·사용자에게 전달 | **이번 PoC 범위 밖** |

자동 머지와 자동 배포는 구현하지 않는다.

## 0. 파일 넣기
이 폴더의 `.github/`와 `poc/`를 오간마음 저장소 루트에 복사 → `CODEOWNERS`의 `@GITHUB_USERNAME`을 본인 계정으로 → main에 커밋.
디스패처는 **항상 깨끗한 main 체크아웃에서** 실행한다. PR 브랜치 안의 디스패처를 검증기로 쓰지 않는다.

## 1. 정책 원문 확인과 Hermes 회고 — `experiments.md` E0, E1

## 2. GitHub 설정
1. **브랜치 규칙(main)**: Settings → Rules → Rulesets
   - Require a pull request, 승인 1명, Require review from Code Owners
   - Required status checks: `analyze-and-test`, `protected-paths`
   - 우회(bypass)는 본인만, "For pull requests only"로. 봇에는 우회를 주지 않는다.
   - **보호 파일을 정상적으로 바꾸는 절차** (오늘은 자동 처리하지 않음): 내가 직접 PR을 열면 `protected-paths`가 실패하고, 내 PR은 내가 CODEOWNER 승인을 할 수 없다. 내용을 직접 검토한 뒤 본인 우회로 머지한다. 디스패처는 이 PR을 다루지 않는다.
2. **PR을 여는 봇** (내 명의 PR은 내가 승인할 수 없다)
   - 권장: 개인 GitHub App (권한: Pull requests read/write, Contents read, Checks read, **Actions read** — 체크 출처 확인에 워크플로 실행 조회가 필요) → 오간마음 저장소에 설치
   - **설치 토큰은 1시간 후 만료된다.** 그래서 고정 토큰 대신 `BOT_GH_TOKEN_CMD`에 "호출할 때마다 새 설치 토큰을 출력하는 명령"을 넣는다. 디스패처가 GitHub를 부를 때마다 이 명령을 실행한다.
     - 예: App ID와 개인 키(.pem)로 JWT를 만들어 `POST /app/installations/{id}/access_tokens`를 호출하고 `token`만 출력하는 작은 스크립트
     - 개인 키 파일은 저장소 밖에 두고, Claude 실행 환경에 노출하지 않는다
   - 간단한 대안: 별도 머신 계정 + fine-grained PAT를 `BOT_GH_TOKEN`에 (GitHub 약관의 머신 계정 규정 확인)
3. **Actions 권한**: Workflow permissions = Read repository contents
4. PR 검증 워크플로에는 비밀정보를 넣지 않는다. 배포·서명은 나중에 main 머지 후 별도 워크플로 + 승인 환경으로.

## 3. GitHub 연결만 먼저 확인 (Claude 실행 없음)
비보호 경로(`lib/` 등)만 바꾸는 작은 커밋으로, 봇 PR·체크 출처·내 Approve 가능 여부를 먼저 확인한다.
```bash
git checkout -b smoke/github-conn && echo "// smoke" >> lib/main.dart && git commit -am "smoke" && git push -u origin smoke/github-conn && git checkout main
python3 poc/dispatcher.py adopt smoke/github-conn
python3 poc/dispatcher.py open-pr <JOB_ID>
python3 poc/dispatcher.py check <JOB_ID> --wait
```
- 확인할 것: PR 작성자가 봇인지, check-run 이름이 `analyze-and-test`·`protected-paths`인지, 출처가 `github-actions` 앱의 `verify.yml`인지(`status`의 근거 기록), **내 계정으로 GitHub Approve가 되는지**
- 확인 후 이 PR은 닫는다 (머지하지 않음)

## 4. 인수 조건 1개
- `poc/acceptance/TEMPLATE.md`를 복사해 작은 기능 하나의 인수 조건을 **직접** 작성
- 그 조건의 테스트를 `test/acceptance/`에 **직접** 작성 (에이전트가 쓰지 않음)
- 위 두 파일은 내 PR로 넣고 우회로 머지
- `poc/jobs/TEMPLATE.md`를 복사해 작업지시서 작성

## 5. 로컬 경로 완주 (오늘의 주 실험)
```bash
claude /login                       # 본인 구독 로그인. ANTHROPIC_API_KEY 가 설정돼 있으면 해제
export BOT_GH_TOKEN_CMD="python3 ~/bin/app_token.py"   # 또는 BOT_GH_TOKEN
python3 poc/dispatcher.py run poc/jobs/<job>.md
```
`run`이 하는 일: 접수 → Claude 실행 → 결과 판정 → **보호 경로 검사** → push → 봇 PR(있으면 재사용) → CI 대기(기본 20분, `CI_TIMEOUT_S`) → 결과 기록. 중간에 실패하면 다음 단계로 가지 않고, **사람 판단 직전에서 멈춘다.**

끝나면:
```bash
python3 poc/dispatcher.py status
# GitHub에서 PR 리뷰 후
python3 poc/dispatcher.py decide <JOB_ID> approve --reason "왜 승인하는지 한 줄"
# GitHub에서 Approve / Merge 는 따로
```
- `decide approve`는 직전에 다시 확인한다: ① 현재 PR head SHA = 검증 SHA ② 같은 SHA의 필수 체크 2개 **최신** 결과가 모두 success(재실행 중·실패면 거부) ③ 체크 출처가 `github-actions` 앱의 `verify.yml` ④ 보호 경로 변경 없음
- 판단 기록에는 SHA와 판단에 쓴 check-run ID·URL이 남는다
- 이 기록은 **그 시점의 사람 판단**이다. GitHub 머지 시점의 필수 체크를 대체하지 않는다

## 6. 중단 실험 (별도 작업)
`run` 실행 중 Ctrl+C → `status`가 `INTERRUPTED`인지, worktree가 어떤 상태인지 기록.

## 7. Routine 비교 (시간이 남으면)
같은 기준 커밋, 같은 작업지시서로.
1. claude.ai/code/routines → New routine → Cloud. 저장소 하나, 환경 Default, **커넥터 전부 제거**, 프롬프트는 `poc/routine-prompt.md`, 트리거는 API
2. ```bash
   export ROUTINE_URL=".../fire" ROUTINE_TOKEN="..."   # 저장소에 커밋 금지
   python3 poc/dispatcher.py fire poc/jobs/<job>.md
   # 세션이 claude/<JOB_ID> 를 push 하면
   python3 poc/dispatcher.py open-pr <JOB_ID>
   python3 poc/dispatcher.py check <JOB_ID> --wait
   ```
- 응답이 불확실하면 재시도하지 않고 `SUBMIT_UNKNOWN` → 세션 확인 후 `reconcile`
- Routine 상태가 초록색이어도 성공이 아니다

## 판정 규칙 (dispatcher.py)
- `VERIFIED` = 필수 체크 2개가 **존재**하고, **현재 PR head 커밋**에 대응하며, **신뢰 출처**(`github-actions` 앱, 같은 SHA의 `verify.yml`·`pull_request` 워크플로 실행에 속한 check suite)이고, **둘 다 success**. 신뢰 출처 안에서 같은 이름이 여러 번 돌았으면 최신 run 기준
- 이름·SHA가 같아도 출처가 다르면 무시한다. check-run과 워크플로 실행은 페이지네이션으로 전부 조회하고, 전체 조회를 확정할 수 없으면 판정 보류(`CHECK_ERROR` 이벤트)
- 누락·`in_progress` → 대기 / skipped·cancelled·neutral → `VERIFY_INCOMPLETE` / failure 등 → `VERIFY_FAILED` / `protected-paths` 실패 → `NEEDS_HUMAN`
- 인증·네트워크·조회 오류는 `CHECK_ERROR` 이벤트로 따로 기록 (검증 실패 아님). 3회 연속이면 `CHECK_ERROR` 상태
- 판정 도중 PR head가 바뀌면 판정하지 않고 다시 대기

## 보호 경계 — 무엇이 실제로 막고 무엇이 막지 못하나
보호 경로: `test/acceptance/`, `poc/`(디스패처 포함), `.github/`, `analysis_options.yaml`, `CODEOWNERS`. 프롬프트·CI·CODEOWNERS·디스패처에서 같은 목록을 쓴다.
- **실제로 막는 것**: 신뢰된 main 체크아웃의 디스패처가 실행 후 `git diff`로 보호 경로 변경을 검사 → `NEEDS_HUMAN`으로 멈추고 PR을 만들지 않음. 승인 직전에도 다시 검사
- **보조 신호**: CI의 `protected-paths`. 보호 경로가 바뀌면 작성자와 무관하게 실패한다. 단, PR이 워크플로 파일 자체를 바꾸면 CI만으로는 보호되지 않는다
- **요청일 뿐인 것**: 프롬프트의 "수정하지 마라". 실제 쓰기 차단이 아니다
- **`--allowedTools`**: 승인 없이 실행해도 되는 도구 목록이다. 도구 제공 범위를 막거나 경로별 쓰기를 차단하는 설정이 아니다. 경로 단위 차단이 필요하면 Claude Code의 권한 규칙(deny)을 별도로 검토한다
- **비밀정보 분리**: Claude 자식 프로세스 환경에서 `BOT_GH_TOKEN`, `BOT_GH_TOKEN_CMD`, `ROUTINE_*`, `GH_TOKEN`, `GITHUB_TOKEN`, `ANTHROPIC_API_KEY`를 제거한다. 디스패처가 쓰는 인증(봇)과 Claude 실행 인증(내 구독 로그인)은 분리돼 있다

## 예산
하루 접수 10건, 동시 진행 2건(`PR_OPEN` 포함), 로컬 최대 40턴. 구독 잔량은 조회 API가 없어서 횟수로만 제한한다.
