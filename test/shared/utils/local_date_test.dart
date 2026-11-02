import 'package:flutter_test/flutter_test.dart';
import 'package:ogan_maum/shared/utils/local_date.dart';

void main() {
  group('isValidLocalDate', () {
    test('정상 날짜를 허용한다', () {
      for (final s in [
        '2026-01-01',
        '2026-12-31',
        '2026-04-30',
        '2026-01-31',
        '1999-11-15',
      ]) {
        expect(isValidLocalDate(s), isTrue, reason: s);
      }
    });

    test('윤년 2월 29일은 허용하고 평년은 거부한다', () {
      expect(isValidLocalDate('2024-02-29'), isTrue);
      expect(isValidLocalDate('2000-02-29'), isTrue);
      expect(isValidLocalDate('2026-02-29'), isFalse);
      expect(isValidLocalDate('1900-02-29'), isFalse);
      expect(isValidLocalDate('2026-02-28'), isTrue);
      expect(isValidLocalDate('2024-02-30'), isFalse);
    });

    test('존재하지 않는 월·일을 거부한다', () {
      for (final s in [
        '2026-99-88',
        '2026-00-10',
        '2026-13-01',
        '2026-01-00',
        '2026-01-32',
        '2026-04-31',
        '2026-06-31',
        '2026-09-31',
        '2026-11-31',
      ]) {
        expect(isValidLocalDate(s), isFalse, reason: s);
      }
    });

    test('0 패딩·자릿수가 맞지 않으면 거부한다', () {
      for (final s in [
        '2026-1-01',
        '2026-01-1',
        '26-01-01',
        '02026-01-01',
        '2026-001-01',
        '2026-01-010',
      ]) {
        expect(isValidLocalDate(s), isFalse, reason: s);
      }
    });

    test('공백·다른 구분자·부가 문자를 거부한다', () {
      for (final s in [
        '',
        ' 2026-01-01',
        '2026-01-01 ',
        '2026-01-01\n',
        '2026/01/01',
        '2026.01.01',
        '20260101',
        '2026-01-01T00:00',
        '2026-01-01Z',
        '+2026-01-01',
        '2026-0a-01',
        '２０２６-01-01',
      ]) {
        expect(isValidLocalDate(s), isFalse, reason: s);
      }
    });
  });

  group('isValidLocalTime', () {
    test('00:00~23:59 경계를 허용한다', () {
      for (final s in ['00:00', '23:59', '12:30', '09:05', '00:59', '23:00']) {
        expect(isValidLocalTime(s), isTrue, reason: s);
      }
    });

    test('범위를 벗어난 시·분을 거부한다', () {
      for (final s in ['25:90', '24:00', '23:60', '99:99', '00:60']) {
        expect(isValidLocalTime(s), isFalse, reason: s);
      }
    });

    test('0 패딩·자릿수가 맞지 않으면 거부한다', () {
      for (final s in ['9:05', '09:5', '009:05', '09:050', '0905']) {
        expect(isValidLocalTime(s), isFalse, reason: s);
      }
    });

    test('공백·다른 구분자·부가 문자를 거부한다', () {
      for (final s in [
        '',
        ' 09:05',
        '09:05 ',
        '09:05\n',
        '09.05',
        '09-05',
        '09 05',
        '09:05:00',
        '-1:00',
        '0a:05',
        '０９:05',
      ]) {
        expect(isValidLocalTime(s), isFalse, reason: s);
      }
    });
  });
}
