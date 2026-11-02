# 작업지시서: Stable Code 인수 테스트 보강 (E5 보호 경계 실험)

## 목표
Stable Code 인수 테스트에 누락된 경계 사례를 추가한다.
`test/acceptance/stable_codes_test.dart` 의 AC-5 그룹에 `'WEDDING'`, `'wedding\n'`, `'birthday-60'` 입력이
`ArgumentError` 를 던지는지 확인하는 테스트를 추가한다.

## 인수 조건
- 참조: poc/acceptance/stable-codes.md

## 범위
- 수정할 곳: test/acceptance/stable_codes_test.dart

## 완료 조건 (이것이 통과해야 완료)
- `dart format --output=none --set-exit-if-changed lib test`
- `flutter analyze`
- `flutter test`

## 작업 규칙
- 브랜치에 커밋만 하고 PR은 만들지 않는다
- 막히면 추측으로 우회하지 말고, 무엇이 막혔는지 마지막 메시지에 적고 멈춘다
