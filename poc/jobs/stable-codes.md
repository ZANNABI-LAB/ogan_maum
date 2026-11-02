# 작업지시서: Stable Code enum 매퍼 구현 (Sprint 0 #20)

## 목표
Sprint 0 Freeze §1 의 Stable Code 4종(relationType, occasionType, direction, followUpStatus)을 Dart enum 으로 만들고,
DB 저장용 코드 문자열과 enum 사이의 명시적 매퍼(`dbCode` / `fromDbCode`)를 구현한다.

## 인수 조건
- 참조: poc/acceptance/stable-codes.md (사람이 승인한 것만)
- 원문: docs/sprint0_freeze.md §1 "Stable Code 정의"
- 인수 테스트: test/acceptance/stable_codes_test.dart (사람이 작성. 읽고 통과시킬 것, 수정 금지)

## 범위
- 수정해도 되는 곳: lib/shared/db/stable_codes.dart (신규), test/shared/db/ (일반 테스트 추가 가능)
- 수정하면 안 되는 곳: test/acceptance/, poc/, .github/, analysis_options.yaml, CODEOWNERS, docs/
  (프롬프트 요청일 뿐 실제 차단은 아님. 디스패처가 실행 후 diff로 검사한다)
- 하지 않는 것: Drift 설치·TypeConverter·테이블 정의, pubspec 의존성 추가, UI 변경

## 구현 요구
- 공개 API 는 인수 조건 문서의 "공개 API 계약"을 그대로 따른다 (파일 경로, enum 이름, 메서드 시그니처, 예외 타입)
- dbCode 는 enum 생성자 인자 등으로 **명시적으로** 지정한다. `.name` 이나 이름 변환(camelCase→snake_case)으로 만들지 않는다
- `fromDbCode` 는 정확히 일치할 때만 변환한다 (trim·대소문자 보정 금지)

## 완료 조건 (이것이 통과해야 완료)
- `dart format --output=none --set-exit-if-changed lib test`
- `flutter analyze`
- `flutter test`

## 작업 규칙
- 브랜치에 커밋만 하고 PR은 만들지 않는다
- 막히면 추측으로 우회하지 말고, 무엇이 막혔는지 마지막 메시지에 적고 멈춘다
- 테스트를 통과시키려고 기존 테스트를 지우거나 약하게 바꾸지 않는다
