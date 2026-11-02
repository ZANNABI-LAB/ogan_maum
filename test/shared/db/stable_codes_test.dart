import 'package:flutter_test/flutter_test.dart';
import 'package:ogan_maum/shared/db/stable_codes.dart';

void main() {
  test('OccasionType 의 snake_case·숫자 코드가 의도한 값에 매핑된다', () {
    expect(OccasionType.firstBirthday.dbCode, 'first_birthday');
    expect(OccasionType.birthday60.dbCode, 'birthday_60');
    expect(
      OccasionType.fromDbCode('first_birthday'),
      OccasionType.firstBirthday,
    );
    expect(OccasionType.fromDbCode('birthday_60'), OccasionType.birthday60);
  });

  test('알 수 없는 코드의 ArgumentError 에 입력값이 담긴다', () {
    expect(
      () => Direction.fromDbCode('sent'),
      throwsA(
        isA<ArgumentError>().having(
          (e) => e.invalidValue,
          'invalidValue',
          'sent',
        ),
      ),
    );
  });

  test('대소문자·공백이 다른 코드는 보정하지 않는다', () {
    expect(() => FollowUpStatus.fromDbCode('Done'), throwsArgumentError);
    expect(() => FollowUpStatus.fromDbCode('done '), throwsArgumentError);
    expect(() => RelationType.fromDbCode('FAMILY'), throwsArgumentError);
  });
}
