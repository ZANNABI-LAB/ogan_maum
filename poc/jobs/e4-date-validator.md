# 작업지시서: 날짜·시간 문자열 검증기 (Sprint 0 R-2) — E4 중단 실험용

## 목표
Sprint 0 Freeze R-2 에 따라 date-only `yyyy-MM-dd` 와 `HH:mm` 문자열을 검증하는 순수 Dart 검증기를 만든다.
`2026-99-88`, `25:90` 같은 값이 저장 경로를 통과하지 못하게 하는 것이 목적이다.

## 인수 조건
- 원문: docs/sprint0_freeze.md §6 R-2
- (이 작업은 중단 실험용이며 사람이 승인한 인수 테스트는 아직 없다)

## 범위
- 수정해도 되는 곳: lib/shared/utils/ (신규), test/shared/utils/ (신규)
- 수정하면 안 되는 곳: test/acceptance/, poc/, .github/, analysis_options.yaml, CODEOWNERS, docs/

## 구현 요구
- `lib/shared/utils/local_date.dart`: `bool isValidLocalDate(String s)`, `bool isValidLocalTime(String s)`
- 형식은 정확히 `yyyy-MM-dd`(0 패딩), `HH:mm`(00:00~23:59). 실제 달력 검증(윤년 포함, 2026-02-29 거부, 2024-02-29 허용)
- 공백·다른 구분자·자릿수 불일치는 거부
- 경계 사례를 충분히 덮는 일반 테스트를 test/shared/utils/ 에 작성

## 완료 조건
- `dart format --output=none --set-exit-if-changed lib test`
- `flutter analyze`
- `flutter test`

## 작업 규칙
- 브랜치에 커밋만 하고 PR은 만들지 않는다
- 막히면 추측으로 우회하지 말고, 무엇이 막혔는지 마지막 메시지에 적고 멈춘다
