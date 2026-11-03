# 개인정보 라벨·관측 조사 (2026-11-03)

> AI 조사 에이전트가 Apple·Google·Sentry·Aptabase·법령 문서에서 수집. "추정"은 공식 확인 안 됨. 법률 자문 아님.

## 결론
- **iOS**: SDK 상시 전송 시 "Data Not Collected" 유지 불가. Apple 은 기기 밖으로 보내 실시간 처리보다 오래 보관하면 "collect", 서드파티 SDK 분도 개발자 신고 https://developer.apple.com/app-store/app-privacy-details/
  - opt-in 이 "Product Improvement Program" 예외 조건(개선 목적, 분명한 opt-in, 기능·가격 동일, 철회 가능, 비연결)을 모두 채우면 신고 생략 가능
- **Android**: SDK 를 넣으면 opt-in 이어도 "수집 안 함" 불가. 예외는 기기 내 처리와 종단간 암호화뿐 https://support.google.com/googleplay/android-developer/answer/10787469

## 사실
- Apple 이 수집하는 데이터(Xcode Organizer 크래시)는 개발자 신고 책임 없음
- Sentry: Flutter SDK 7.20.1+ Privacy Manifest 포함, 기본 `sendDefaultPii=false`, 설치 단위 무작위 ID, HTTP URL·브레드크럼 기본 수집, 무료 5k 에러/월 https://docs.sentry.io/platforms/dart/guides/flutter/data-management/data-collected/ · https://sentry.io/pricing/
- Aptabase: 이벤트·앱/OS 버전·기기 모델·로케일·세션 ID, IP 로 국가 추정 후 미저장, 5년 보관, 월 2만 이벤트 무료 https://aptabase.com/docs.md
- 스토어 콘솔: Xcode Organizer(공유 동의 사용자), Android vitals(진단 공유 동의 사용자). 앱이 죽지 않는 Dart 예외는 거의 안 보임 (추정)
- 처리방침: Apple 가이드라인 5.1.1(i) 모든 앱 필수, Google 은 수집 없어도 URL 필요
- 개인정보보호법 제2조 5호·제30조: 개발자가 접근할 수 없는 기기 내 지인 정보는 개발자의 "처리"가 아닐 가능성 (추정). SDK 도입 시 국외이전·위탁 고지 필요로 보는 것이 안전 https://casenote.kr/법령/개인정보_보호법/제30조

## 옵션
| 옵션 | iOS 라벨 | Android 라벨 | 얻는 정보 |
|---|---|---|---|
| **A 스토어 콘솔만** | Not Collected | 수집 안 함 | 동의 사용자의 네이티브 크래시·ANR |
| B Sentry 상시 | Crash·Performance (Not Linked) | Crash logs·Diagnostics | Dart 예외·스택 |
| C Sentry+Aptabase | B + Product Interaction, Coarse Location | B + App interactions, 대략 위치 | 기능 사용량 |
| D opt-in 진단 | 조건 충족 시 Not Collected | 선택적 수집 표기 | 동의자 Dart 예외 |

## 채택 (D-08): A + 출시 전 내부 테스트 빌드에서만 Sentry
- 내부 테스트 트랙만 쓰는 앱은 Data safety 신고서 작성 불필요 (10787469)
