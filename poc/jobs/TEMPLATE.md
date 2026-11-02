# 작업지시서: <짧은 제목>

## 목표
<무엇을 만들거나 고치는지 2~3문장>

## 인수 조건
- 참조: poc/acceptance/<파일명>.md (사람이 승인한 것만)

## 범위
- 수정해도 되는 곳: lib/..., test/(acceptance 제외)
- 수정하면 안 되는 곳: test/acceptance/, poc/, .github/, analysis_options.yaml, CODEOWNERS
  (프롬프트 요청일 뿐 실제 차단은 아님. 디스패처가 실행 후 diff로 검사한다)

## 완료 조건 (이것이 통과해야 완료)
- `dart format --output=none --set-exit-if-changed lib test`
- `flutter analyze`
- `flutter test`

## 작업 규칙
- 브랜치에 커밋만 하고 PR은 만들지 않는다
- 막히면 추측으로 우회하지 말고, 무엇이 막혔는지 마지막 메시지에 적고 멈춘다
- 테스트를 통과시키려고 기존 테스트를 지우거나 약하게 바꾸지 않는다
