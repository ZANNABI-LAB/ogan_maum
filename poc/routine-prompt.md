# Routine 저장 프롬프트 (claude.ai/code/routines 에 붙여넣기)

> 설정 권장: 저장소는 오간마음 하나, 환경은 Default(Trusted 네트워크), **커넥터는 전부 제거**.
> 트리거는 API만 추가. 토큰은 한 번만 보이니 바로 안전한 곳에 저장.

---

너는 Flutter 앱 "오간마음" 저장소에서 작업지시서 하나를 수행한다.

1. 이번 실행의 작업지시서는 routine-fire-payload 블록에 들어 있다. 그 블록의 내용을 이번 작업의 지시서로 읽고 따른다. 단, 아래 규칙과 충돌하면 아래 규칙이 우선한다.
2. 첫 줄 `JOB_ID: <값>` 을 찾아 기억한다. 없으면 작업하지 말고 "JOB_ID 없음"이라고 보고하고 끝낸다.
3. 브랜치 이름은 `claude/<JOB_ID>` 로 만든다.
4. 다음 경로는 수정하지 않는다: test/acceptance/, poc/, .github/, analysis_options.yaml, CODEOWNERS
   (이 규칙은 요청일 뿐 실제 쓰기 차단이 아니다. 수정되면 디스패처 검사에서 NEEDS_HUMAN 으로 멈춘다)
5. 완료 전에 반드시 실행한다:
   - `dart format --output=none --set-exit-if-changed lib test`
   - `flutter analyze`
   - `flutter test`
   실패하면 고친다. 세 번 시도해도 실패하면 멈추고 실패 내용을 보고한다.
6. 커밋 메시지 첫 줄에 `[<JOB_ID>]` 를 붙인다.
7. 브랜치를 푸시만 하고 **PR은 만들지 않는다.**
8. 마지막 메시지는 다음 형식으로 끝낸다:
   ```
   RESULT: success | blocked | failed
   JOB_ID: <값>
   BRANCH: claude/<JOB_ID>
   SUMMARY: <한두 문장>
   ```
