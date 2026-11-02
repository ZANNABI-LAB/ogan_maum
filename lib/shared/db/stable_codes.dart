// Stable Code enum 과 DB 코드 매퍼.
// 기준: docs/sprint0_freeze.md §1 "Stable Code 정의"
//
// dbCode 는 생성자 인자로 명시한다. `enumValue.name` 에 의존하지 않으므로
// Dart 이름을 바꿔도 DB 에 저장된 코드는 바뀌지 않는다.
// fromDbCode 는 정확히 일치할 때만 변환하고, 그 외에는 ArgumentError 를 던진다.

T _fromDbCode<T extends Enum>(
  List<T> values,
  String Function(T) dbCodeOf,
  String code,
  String typeName,
) {
  for (final v in values) {
    if (dbCodeOf(v) == code) return v;
  }
  throw ArgumentError.value(code, 'code', 'Unknown $typeName dbCode');
}

enum RelationType {
  family('family'),
  relative('relative'),
  friend('friend'),
  work('work'),
  acquaintance('acquaintance'),
  other('other');

  const RelationType(this.dbCode);

  final String dbCode;

  static RelationType fromDbCode(String code) =>
      _fromDbCode(values, (v) => v.dbCode, code, 'RelationType');
}

enum OccasionType {
  wedding('wedding'),
  funeral('funeral'),
  firstBirthday('first_birthday'),
  birthday60('birthday_60'),
  opening('opening'),
  other('other');

  const OccasionType(this.dbCode);

  final String dbCode;

  static OccasionType fromDbCode(String code) =>
      _fromDbCode(values, (v) => v.dbCode, code, 'OccasionType');
}

enum Direction {
  received('received'),
  given('given');

  const Direction(this.dbCode);

  final String dbCode;

  static Direction fromDbCode(String code) =>
      _fromDbCode(values, (v) => v.dbCode, code, 'Direction');
}

enum FollowUpStatus {
  none('none'),
  pending('pending'),
  done('done');

  const FollowUpStatus(this.dbCode);

  final String dbCode;

  static FollowUpStatus fromDbCode(String code) =>
      _fromDbCode(values, (v) => v.dbCode, code, 'FollowUpStatus');
}
