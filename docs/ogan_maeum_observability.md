# 오간마음 — Observability 플랜 (Aptabase + Sentry)

> Sprint 0 Freeze를 건드리지 않는 애드온 플랜.
> 원칙: 장부 데이터(금액·이름·관계·메모)는 어떤 이벤트에도 절대 포함하지 않는다.

---

## 1. 어디서 확인하나

### Aptabase (사용 통계)
- **aptabase.com 웹 대시보드** — 앱 등록 후 App Key 발급, 대시보드에서 확인
- 보이는 것: 일별 세션/활성 사용자, OS·앱 버전 분포, 국가, 커스텀 이벤트별 발생 수와 속성 분해
- 모바일 브라우저로도 접근 가능 (별도 앱 없음)
- 데이터는 SDK → Aptabase 클라우드로 직접 전송. 우리 서버 불필요

### Sentry (크래시/에러)
- **sentry.io 웹 대시보드** — 프로젝트(Flutter) 생성 후 DSN 발급
- 보이는 것: 크래시별 스택트레이스(디심볼리케이션), 발생 기기/OS/앱 버전, 발생 빈도와 영향 사용자 수, 릴리즈별 crash-free rate
- **알림**: 신규 이슈/급증 시 이메일 알림 기본 제공. 심각한 크래시는 대시보드 들어가기 전에 메일로 먼저 안다
- 무료 티어로 인디 규모 충분

---

## 2. 코드 구조 (계층 규율 R-1과 정합)

SDK를 직접 호출하는 코드가 앱 전체에 퍼지지 않도록 추상 인터페이스 뒤에 숨긴다.

```dart
// shared/observability/analytics_service.dart
abstract interface class AnalyticsService {
  void track(String event, [Map<String, Object> props = const {}]);
}

class NoopAnalytics implements AnalyticsService {
  @override
  void track(String event, [Map<String, Object> props = const {}]) {}
}

class AptabaseAnalytics implements AnalyticsService { ... } // Sprint 3

// 크래시는 Sentry SDK 초기화(main)로 충분 — 별도 인터페이스 불필요.
// 단, 수동 캡처가 필요하면 CrashReporter 인터페이스로 동일 패턴.
```

- Riverpod Provider로 주입. **디버그 빌드 = NoopAnalytics**, 릴리즈 빌드 = AptabaseAnalytics
- 테스트에서는 Noop 또는 fake로 주입 — 테스트가 네트워크를 만지지 않는다

## 3. 이벤트 스키마 (v1 전체 목록 — 이것만 추적)

| 이벤트 | 속성 | 목적 |
|---|---|---|
| quick_input_started | entry_point (fab/guide) | 퍼널 시작 |
| quick_input_step | step (1/2/3) | 이탈 지점 |
| quick_input_completed | duration_ms, is_new_person | **핵심 지표: 10초** |
| quick_input_abandoned | last_step | 이탈 분석 |
| record_searched | has_filter | 검색 사용률 |
| guide_opened | category | 가이드 소비 |
| guide_message_copied | category | 킬러 기능 검증 |
| csv_exported | — | 유틸 사용률 |
| app_lock_enabled | — | 보안 기능 채택률 |

금지: 금액, 이름, 관계, 그룹명, 메모, 이벤트 제목 등 사용자 입력값 일체. 속성은 위 표에 명시된 것만 — 새 속성 추가는 이 문서 갱신과 함께.

## 4. 스프린트 배치 (Freeze 존중)

- **Sprint 0**: `shared/observability/` 에 인터페이스 + Noop만 추가. SDK 미설치, 네트워크 없음. (구조 결정이므로 지금, 구현은 아니므로 Freeze 위반 아님)
- **Sprint 1~2**: 화면 코드에 track() 호출만 심는다 — Noop이라 아무 일도 안 일어남
- **Sprint 3 (출시 준비)**: `aptabase_flutter`, `sentry_flutter` 설치, 릴리즈 빌드에만 활성화, Sentry 릴리즈/dSYM 업로드 세팅, 이메일 알림 확인
- **Sprint 3 스토어 작업 변경**: iOS 개인정보 라벨 "사용 데이터(익명) 수집"으로 신고, Play 데이터 보안 섹션 동일, 개인정보처리방침에 두 서비스 명시. 문구: "장부 기록은 기기에만 저장됩니다. 앱 개선을 위한 익명 사용 통계와 오류 정보만 수집합니다."

## 5. Sprint 3 DoD 추가분

- 릴리즈 빌드에서 Aptabase 대시보드에 quick_input_completed 이벤트 도착 확인
- 강제 크래시 테스트로 Sentry 이슈 생성 + 이메일 알림 수신 확인
- 디버그 빌드에서 두 SDK 모두 미전송 확인
- 스토어 라벨/처리방침 갱신 완료
