# 인수 조건: Stable Code enum 매퍼

> 이 파일은 **사람이 쓰고 승인한다.** 에이전트는 읽기만 한다.
> 이 파일이 바뀐 PR은 디스패처의 보호 경로 검사에서 NEEDS_HUMAN 이 되어 자동 처리되지 않는다.
> (CI의 protected-paths 는 보조 신호다. PR이 워크플로를 바꾸면 CI만으로는 보호되지 않는다)

- 승인자: @SHINJUNGSUN
- 승인일: 2026-11-02
- 관련 기준: `docs/sprint0_freeze.md` §1 "Stable Code 정의", §5 테스트 #20

## 원문 (Sprint 0 Freeze §1, 그대로 인용)
```text
relationType : family | relative | friend | work | acquaintance | other
occasionType : wedding | funeral | first_birthday | birthday_60 | opening | other
direction    : received | given
followUpStatus: none | pending | done
```
> 각 enum에 `String get dbCode` / `fromDbCode()` 매퍼를 두고 Drift TypeConverter로 연결한다. `enumValue.name` 직접 저장 금지.

## 공개 API 계약 (인수 테스트가 이 이름으로 import 한다)
- 파일: `lib/shared/db/stable_codes.dart` (import: `package:ogan_maum/shared/db/stable_codes.dart`)
- enum 4개: `RelationType`, `OccasionType`, `Direction`, `FollowUpStatus`
- 각 enum: 인스턴스 getter `String get dbCode`, 정적 메서드 `static <Enum> fromDbCode(String code)`
- 알 수 없는 코드: `fromDbCode` 는 `ArgumentError` 를 던진다 (승인자 확인 2026-11-02)
- 순수 Dart. 외부 패키지·Flutter 의존 없음. Drift TypeConverter 는 이번 범위 밖

## 반드시 성립해야 하는 것 (기능)
- [ ] AC-1: 4개 enum의 값 개수와 dbCode 집합이 원문과 **정확히** 같다 (누락·추가 없음)
- [ ] AC-2: 모든 값에서 `fromDbCode(v.dbCode) == v` (왕복 전수)
- [ ] AC-3: 모든 원문 코드 문자열 c 에서 `fromDbCode(c).dbCode == c`
- [ ] AC-4: `first_birthday`, `birthday_60` 처럼 Dart 식별자와 다른 코드도 원문 문자열 그대로 나온다
- [ ] AC-5: 원문에 없는 코드(`''`, `'Wedding'`, `'firstBirthday'`, `' wedding'`)는 `ArgumentError`

## 절대 깨지면 안 되는 것 (데이터 불변식)
- [ ] dbCode 는 `enumValue.name` 에 의존하지 않는다 (Dart 이름을 바꿔도 DB 코드는 불변 — 명시적 매핑)
- [ ] 대소문자·공백을 보정하지 않는다 (정확히 일치할 때만 변환)

## 판정 방법
- 각 AC를 검증하는 테스트는 `test/acceptance/stable_codes_test.dart` 에 **사람이 작성·승인**한다
- 에이전트가 추가하는 테스트는 `test/` 아래 일반 테스트로 두고, 인수 판정에는 쓰지 않는다
