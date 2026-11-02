/// Sprint 0 Freeze R-2: 저장 경로에 들어가는 date-only·time 문자열 검증.
///
/// DB CHECK 없이 Repository 진입점에서 이 함수들로 잘못된 값을 걸러낸다.
library;

final RegExp _datePattern = RegExp(r'^([0-9]{4})-([0-9]{2})-([0-9]{2})$');
final RegExp _timePattern = RegExp(r'^([0-9]{2}):([0-9]{2})$');

/// [s] 가 정확히 `yyyy-MM-dd` 형식이고 실제 달력에 존재하는 날짜면 true.
///
/// 윤년은 그레고리력 규칙(4의 배수, 100의 배수 제외, 400의 배수 포함)을 따른다.
bool isValidLocalDate(String s) {
  final match = _datePattern.firstMatch(s);
  if (match == null) return false;
  final year = int.parse(match.group(1)!);
  final month = int.parse(match.group(2)!);
  final day = int.parse(match.group(3)!);
  if (month < 1 || month > 12) return false;
  return day >= 1 && day <= _daysInMonth(year, month);
}

/// [s] 가 정확히 `HH:mm` 형식이고 00:00~23:59 범위면 true.
bool isValidLocalTime(String s) {
  final match = _timePattern.firstMatch(s);
  if (match == null) return false;
  final hour = int.parse(match.group(1)!);
  final minute = int.parse(match.group(2)!);
  return hour <= 23 && minute <= 59;
}

int _daysInMonth(int year, int month) {
  switch (month) {
    case 2:
      return _isLeapYear(year) ? 29 : 28;
    case 4:
    case 6:
    case 9:
    case 11:
      return 30;
    default:
      return 31;
  }
}

bool _isLeapYear(int year) =>
    (year % 4 == 0 && year % 100 != 0) || year % 400 == 0;
