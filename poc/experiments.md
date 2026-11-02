# M0 실험 기록

> 판정은 Claude의 요약이 아니라 원본 로그·PR·CI 결과로 한다.
> **모의 검증**과 **실제 서비스 검증**을 구분한다. 실제로 실행하지 않은 항목은 **미실행**으로 남기고 추정으로 채우지 않는다.

## A. 모의 검증 (가짜 claude·gh, 외부 서비스 호출 없음) — 2026-10-31 완료
| # | 사례 | 결과 |
|---|---|---|
| 1 | 필수 체크 누락 | VERIFIED 아님 → 대기 후 VERIFY_TIMEOUT |
| 2 | analyze-and-test skipped | VERIFY_INCOMPLETE |
| 3 | pending / gh rc=8 / 다른 SHA 체크만 | 예외 없이 대기 |
| 4 | 인증 오류(401) | CHECK_ERROR 이벤트, 상태 유지 |
| 5 | 체크 실패 / protected-paths 실패 | VERIFY_FAILED / NEEDS_HUMAN |
| 6 | 두 체크 통과(재실행 시 최신 run 기준) | VERIFIED + 검증 SHA·check-run 근거 저장 |
| 7 | 같은 이름·SHA지만 다른 출처만 존재 | VERIFIED 아님 (대기) |
| 8 | 신뢰 체크 통과 + 다른 출처의 같은 이름 실패(더 최신) | 다른 출처 무시, VERIFIED |
| 9 | 결과 150개, 필수 체크가 2페이지 | 2페이지까지 조회 후 VERIFIED |
| 10 | total_count가 실제보다 큼 | 판정 보류 (VERIFIED 아님) |
| 11 | VERIFIED 이후 같은 SHA 재실행 중 | 승인 거부 → PR_OPEN |
| 12 | VERIFIED 이후 같은 SHA 재실행 실패 | 승인 거부 → VERIFY_FAILED |
| 13 | 검증 후 PR head 변경 | 승인 거부 |
| 14 | 정상 승인 | HUMAN_APPROVED, decisions에 SHA + check-run ID·URL |
| 15 | 보호 경로 변경 | PR 생성 전 NEEDS_HUMAN |
| 16 | 기존 PR 존재 | 재사용, 중복 생성 없음, 승인 상태 유지 |
| 17 | Claude 자식 환경 | 봇·루틴 토큰, GH_TOKEN, ANTHROPIC_API_KEY 제거 |

---

## B. 실제 서비스 검증

### 공통 증거 (각 실험마다 채운다)
- 실행 시작 기준 커밋 SHA (main):
- Claude CLI 버전 / gh 버전 / git 버전: (`poc/runs/<JOB_ID>/summary.json` 의 versions)
- PR URL / PR head SHA:
- 필수 check-run ID·URL: analyze-and-test = / protected-paths =
- 사람 판단 대상 SHA / 판단 이유:
- 사람이 개입한 횟수와 소요 시간: (최초 접수 이후 내가 직접 실행한 명령 수, 화면을 본 시간)

### E0. Hermes 회고 (3줄) — 미실행
- 무엇이 막혔나:
- 왜 (정책인가 기술인가):
- 이번에 막는 장치:

### E1. 정책 원문 확인 — 미실행
- 가설: 본인 구독으로 공식 Claude Code(`claude -p`, Routine)를 개인 용도로 쓰는 것은 허용 범위다
- 읽을 것: https://code.claude.com/docs/en/legal-and-compliance · https://support.claude.com/en/articles/15036540 · https://www.anthropic.com/legal/consumer-terms · OpenAI Codex 인증 문서
- 증거(인용 + URL) / 결정: 괜찮음 · 불확실 · 안 됨

### E2. GitHub 연결 확인 (Claude 실행 없음) — 미실행
- 절차: README 3단계 (`adopt` → `open-pr` → `check --wait`)
- 확인: PR 작성자 = 봇 / 실제 check-run 이름 / 출처(app slug, workflow path, check_suite_id) / 내 계정 Approve 가능 여부 / 토큰 갱신(BOT_GH_TOKEN_CMD) 동작
- 증거: PR URL, check-run ID·URL, `status` 출력
- 결정:

### E3. 로컬 경로 완주 (`run`) — 미실행
- 가설: 최초 접수 후 추가 수동 명령 없이 봇 PR + 필수 체크 2개 통과까지 도착한다
- 증거: 공통 증거 전부 + `poc/runs/<JOB_ID>/`
- 성공 판정: VERIFIED → `decide approve` 기록 SHA = 검증 SHA, check-run 근거와 이유 기록
- 결정:

### E4. 중단 실험 (별도 작업) — 미실행
- 절차: `run` 중 Ctrl+C → `status` → worktree 확인
- 확인: INTERRUPTED 기록, worktree dirty 여부, `claude --resume` 가능 여부

### E5. 보호 경계 — 미실행
- `test/acceptance/`를 수정하라는 작업지시서로 `run` → PR 생성 전 NEEDS_HUMAN 되는지

### E6. Routine 비교 (같은 기준 커밋·같은 작업지시서) — 미실행
- 확인: session_id/url, 브랜치 push, 실행 시간, 구독 사용량 변화, CI 결과

## 오늘의 결론
- 성공 기준 충족 여부:
- 주력 실행 경로:
- 남은 제약:
- 다음 단계:
