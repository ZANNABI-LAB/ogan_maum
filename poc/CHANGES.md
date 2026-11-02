# 변경 이력

## v0.3.1 (E2 실제 실행 중 발견)
- `decide approve`·`check` 가 PR state 를 확인하지 않아 닫힌 PR 에도 HUMAN_APPROVED 가 기록되던 문제 수정: decide 는 OPEN 아니면 거부, check 는 `PR_CLOSED` 기록
- README: `BOT_GH_TOKEN_CMD` 는 셸 없이 실행되므로 절대경로 필요

## v0.3 (두 번째 독립 리뷰 반영) — 범위 확대 없음

### 수정 사항
1. **protected-paths 작성자 예외 제거**: 보호 경로 변경이 없으면 작성자와 무관하게 통과, 있으면 실패. 소유자 자동 통과 예외 삭제. CODEOWNERS·필수 리뷰 유지. 보호 파일을 정상적으로 바꾸는 절차(내가 검토 후 본인 우회 머지, 자동 처리 안 함)를 README에 분리 기술.
2. **check-run 출처·전체 조회**: `app.slug == github-actions`이고, check suite가 같은 SHA의 `.github/workflows/verify.yml`(`pull_request`) 워크플로 실행에 속한 체크만 신뢰. check-run(`filter=all`)과 워크플로 실행을 페이지네이션으로 전부 조회하고, `total_count`와 맞지 않으면 판정 보류. 신뢰 출처 안에서만 최신 재실행 선택.
3. **승인 직전 재확인**: `decide approve` 직전에 PR head SHA = 검증 SHA, 같은 SHA 필수 체크 2개 최신 결과 success, 신뢰 출처, 보호 경로 변경 없음을 모두 다시 확인. 하나라도 아니면 승인 거부하고 상태를 되돌림. `decisions`에 SHA와 check-run ID·URL 기록. 이 기록이 머지 시점 필수 체크를 대체하지 않음을 출력·README에 명시.
4. **최소 보조 기능**: `adopt <branch>` — 이미 push된 브랜치를 장부에 등록해 Claude 없이 GitHub 연결만 확인. `run` 요약에 기준 커밋 SHA와 claude/gh/git 버전 기록. README에 GitHub App 권한 `Actions read` 추가.

### 모의 검증 결과 (외부 서비스 호출 없음)
가짜 `claude`·가짜 `gh`(check-runs·workflow runs 페이지네이션 지원)·로컬 bare 원격으로 17개 사례를 확인했다. 상세는 `poc/experiments.md` A절.
- 신규: 다른 출처 동일 이름 → 무시 ✅ · 다른 출처만 존재 → VERIFIED 아님 ✅ · 2페이지 결과 → 전부 조회 후 판정 ✅ · 조회 불완전 → 판정 보류 ✅ · VERIFIED 후 재실행 중/실패 → 승인 거부 ✅
- 회귀: v0.2의 9개 사례 모두 동일하게 통과 ✅

### 실제 실행 결과
- 없음. Claude·GitHub·Routine 실제 호출은 하지 않았다. `experiments.md` B절은 전부 **미실행**.

### 남은 제약 (실제 환경에서 확인 필요)
- 실제 check-run의 `app.slug`, workflow run의 `path` 형식(`.github/workflows/verify.yml` 또는 `@ref` 접미사)과 `check_suite_id` 연결이 가정대로인지 → E2에서 확인
- GitHub App 토큰 권한(Checks·Actions read 포함)으로 check-runs·actions/runs 조회가 되는지
- `gh api`의 `{owner}/{repo}` 자리표시자가 봇 토큰 환경에서 저장소를 올바르게 잡는지
- 실제 `claude -p` 플래그 조합과 result 이벤트 `subtype` 값, 허용 도구만으로 `flutter test`까지 승인 없이 끝나는지
- 봇 PR을 내 계정으로 Approve 할 수 있는지, 본인 우회 설정이 의도대로인지
- 정책 원문(E1)

---

## v0.2 (첫 번째 독립 리뷰 반영)
- 필수 체크 2개·SHA 기준 판정, 조회 오류 분리, rc=8 대기
- 검증 SHA 저장, 승인 직전 PR head 재조회, decisions에 SHA
- 로컬 경로 `run` 완주(실행→보호검사→push→봇 PR 재사용→CI 대기→기록), 사람 판단 직전 종료
- `decide approve` → `HUMAN_APPROVED` (GitHub 승인·머지와 구분)
- 보호 경로 통일, 신뢰된 디스패처의 git diff 검사, Claude 자식 환경 비밀정보 제거, 봇 토큰 갱신(`BOT_GH_TOKEN_CMD`)
- 모의 검증 중 발견: PR 재사용 시 승인 상태가 되돌아가던 버그 수정
