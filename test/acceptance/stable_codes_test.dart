// 인수 테스트: Stable Code enum 매퍼
// 기준: poc/acceptance/stable-codes.md, docs/sprint0_freeze.md §1 "Stable Code 정의"
// 원문 코드는 구현에서 가져오지 않고 이 파일에 리터럴로 고정한다.
import 'package:flutter_test/flutter_test.dart';
import 'package:ogan_maum/shared/db/stable_codes.dart';

// Sprint 0 Freeze §1 원문 그대로
const relationTypeCodes = {
  'family',
  'relative',
  'friend',
  'work',
  'acquaintance',
  'other',
};
const occasionTypeCodes = {
  'wedding',
  'funeral',
  'first_birthday',
  'birthday_60',
  'opening',
  'other',
};
const directionCodes = {'received', 'given'};
const followUpStatusCodes = {'none', 'pending', 'done'};

const invalidCodes = ['', 'Wedding', 'firstBirthday', ' wedding'];

void main() {
  group('AC-1 값 개수와 dbCode 집합이 원문과 정확히 같다', () {
    test('relationType', () {
      expect(RelationType.values.length, relationTypeCodes.length);
      expect(
        RelationType.values.map((v) => v.dbCode).toSet(),
        relationTypeCodes,
      );
    });
    test('occasionType', () {
      expect(OccasionType.values.length, occasionTypeCodes.length);
      expect(
        OccasionType.values.map((v) => v.dbCode).toSet(),
        occasionTypeCodes,
      );
    });
    test('direction', () {
      expect(Direction.values.length, directionCodes.length);
      expect(Direction.values.map((v) => v.dbCode).toSet(), directionCodes);
    });
    test('followUpStatus', () {
      expect(FollowUpStatus.values.length, followUpStatusCodes.length);
      expect(
        FollowUpStatus.values.map((v) => v.dbCode).toSet(),
        followUpStatusCodes,
      );
    });
  });

  group('AC-2 모든 값에서 fromDbCode(v.dbCode) == v', () {
    test('relationType', () {
      for (final v in RelationType.values) {
        expect(RelationType.fromDbCode(v.dbCode), v);
      }
    });
    test('occasionType', () {
      for (final v in OccasionType.values) {
        expect(OccasionType.fromDbCode(v.dbCode), v);
      }
    });
    test('direction', () {
      for (final v in Direction.values) {
        expect(Direction.fromDbCode(v.dbCode), v);
      }
    });
    test('followUpStatus', () {
      for (final v in FollowUpStatus.values) {
        expect(FollowUpStatus.fromDbCode(v.dbCode), v);
      }
    });
  });

  group('AC-3 원문 코드 c 에서 fromDbCode(c).dbCode == c', () {
    test('relationType', () {
      for (final c in relationTypeCodes) {
        expect(RelationType.fromDbCode(c).dbCode, c);
      }
    });
    test('occasionType', () {
      for (final c in occasionTypeCodes) {
        expect(OccasionType.fromDbCode(c).dbCode, c);
      }
    });
    test('direction', () {
      for (final c in directionCodes) {
        expect(Direction.fromDbCode(c).dbCode, c);
      }
    });
    test('followUpStatus', () {
      for (final c in followUpStatusCodes) {
        expect(FollowUpStatus.fromDbCode(c).dbCode, c);
      }
    });
  });

  group('AC-4 Dart 식별자와 다른 코드도 원문 문자열 그대로', () {
    test('first_birthday', () {
      expect(
        OccasionType.fromDbCode('first_birthday').dbCode,
        'first_birthday',
      );
    });
    test('birthday_60', () {
      expect(OccasionType.fromDbCode('birthday_60').dbCode, 'birthday_60');
    });
  });

  group('AC-5 원문에 없는 코드는 ArgumentError (보정 없음)', () {
    for (final c in invalidCodes) {
      test('"$c"', () {
        expect(() => RelationType.fromDbCode(c), throwsArgumentError);
        expect(() => OccasionType.fromDbCode(c), throwsArgumentError);
        expect(() => Direction.fromDbCode(c), throwsArgumentError);
        expect(() => FollowUpStatus.fromDbCode(c), throwsArgumentError);
      });
    }
    test('다른 enum 의 코드는 거부 (교차 혼입 없음)', () {
      expect(() => RelationType.fromDbCode('wedding'), throwsArgumentError);
      expect(() => Direction.fromDbCode('pending'), throwsArgumentError);
      expect(() => FollowUpStatus.fromDbCode('given'), throwsArgumentError);
    });
  });

  group('불변식: dbCode 는 enumValue.name 에 의존하지 않는다', () {
    test('Dart 이름과 다른 코드를 가진 값이 존재한다', () {
      // 원문에 snake_case·숫자 코드가 있으므로 .name 그대로라면 AC-1에서 실패한다.
      // 여기서는 그 차이가 실제로 존재함을 명시적으로 고정한다.
      final differing = OccasionType.values.where((v) => v.dbCode != v.name);
      expect(
        differing.map((v) => v.dbCode).toSet(),
        containsAll(['first_birthday', 'birthday_60']),
      );
    });
  });
}
