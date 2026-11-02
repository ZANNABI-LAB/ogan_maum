# 오간마음 — 구현 플랜 v1

> 경조사비·축의금·부의금 장부 + 경조사 예절 가이드. ZANNABI LAB 컴팩트 앱 라인 1호.
> 원칙: **기능 1개 중심, 완전 로컬(서버 없음), 2주 출시.**

---

## 1. 제품 개요

- **한 줄 정의**: 주고받은 경조사비를 기록하고, 경조사 예절까지 알려주는 앱
- **타깃**: 경조사비를 주고받는 모든 한국 성인 (30~50대 중심)
- **차별점**:
  1. 장부 + 예절 가이드 + 상황별 문자 문구 복사 (경쟁 앱은 장부만)
  2. 완전 로컬 — "당신의 기록은 폰 밖으로 나가지 않습니다"
  3. 3스텝 빠른 입력 (경쟁 앱 대비 입력 UX 최우선)
- **스토어**: iOS 참고(Reference, 보조 라이프스타일) / Play 라이프스타일
- **앱 이름**: `오간마음 - 경조사비·축의금 장부`
- **키워드**: 경조사, 축의금, 부의금, 부조금, 조의금, 장부, 답례, 조문

## 2. 기술 스택

| 영역 | 선택 | 비고 |
|---|---|---|
| 프레임워크 | Flutter (stable) | 복권 앱 등 코어 재활용 전제 |
| 상태관리 | Riverpod 2.x | |
| DB | Drift + sqlcipher_flutter_libs | DB 파일 암호화 |
| 앱 잠금 | local_auth | 생체인증 + PIN 폴백 |
| 차트 | fl_chart | |
| 내보내기 | csv + share_plus | |
| 알림 | flutter_local_notifications | 답례 리마인더 |
| 라우팅 | go_router | |

- 서버/로그인/외부 API **없음**. 예절 콘텐츠는 `assets/etiquette_content.json` (완성본 있음)
- 백업: 기기 클라우드 백업(iCloud/Google) + CSV 내보내기. v1.1에서 자체 백업 파일(.ogan) 검토

## 3. 폴더 구조 (FSD-lite)

```
lib/
  app/            # 엔트리, 라우터, 테마
  features/
    ledger/       # 기록 CRUD, 빠른 입력, 리스트/검색
    person/       # 지인 관리, 지인별 상세(차액/답례)
    etiquette/    # 예절 가이드, 문구 복사
    stats/        # 통계 대시보드
    settings/     # 앱 잠금, 내보내기, 알림 설정
  shared/
    db/           # Drift 스키마, DAO  ← 복권 앱 재활용 대상
    ui/           # 공통 위젯, 금액 포맷터
    utils/
```

## 4. 데이터 모델 (Drift)

### persons
| 컬럼 | 타입 | 비고 |
|---|---|---|
| id | int PK autoincrement | |
| name | text | required |
| relation | text enum | 가족/친척/친구/직장/지인/기타 |
| memo | text nullable | |
| createdAt | datetime | |

### events
| 컬럼 | 타입 | 비고 |
|---|---|---|
| id | int PK | |
| type | text enum | 결혼/장례/돌/회갑/개업/기타 |
| title | text | 예: "김OO 결혼식" |
| date | date | |
| place | text nullable | |
| memo | text nullable | |

### transactions
| 컬럼 | 타입 | 비고 |
|---|---|---|
| id | int PK | |
| personId | FK → persons | indexed |
| eventId | FK → events nullable | 빠른 입력 시 이벤트 생략 허용 |
| direction | text enum | received / given |
| amount | int | 원 단위 |
| method | text enum | 현금/이체/기타 |
| thanked | bool default false | 답례 완료 여부 |
| memo | text nullable | |
| date | date | 이벤트 없을 때의 기준일 |

### 파생 쿼리 (뷰/DAO 메서드)
- 지인별: `sum(received) - sum(given)` = 차액 → 양수면 "답례 필요" 배지
- 월별/관계별/이벤트타입별 합계 (통계 탭)
- 검색: 이름 + 이벤트명 LIKE, 필터: direction/type/기간

## 5. 화면 명세 (4탭)

### 5.1 홈
- 이번 달 요약 카드 (받음/줌/건수)
- 답례 필요 목록 (차액 양수 + thanked=false)
- 다가오는 이벤트 (date >= today)

### 5.2 기록
- 거래 리스트 (최신순, 월 구분 헤더) + 검색/필터
- **FAB → 빠른 입력 3스텝** (이 앱의 핵심 UX):
  1. 이름 입력 (기존 지인 자동완성, 없으면 즉석 생성)
  2. 이벤트 타입 칩 선택 + 받음/줌 토글
  3. 금액 (5/10/20만 프리셋 버튼 + 직접 입력) → 저장
  - 목표: 신규 기록 10초 이내
- 항목 탭 → 상세/수정/삭제, 지인 탭 → 지인별 히스토리

### 5.3 예절 가이드
- 카테고리 카드 5개 (JSON 파싱): 장례/결혼/돌/개업/회갑
- 상세: sections 아코디언 + messages 리스트(복사 버튼, 스낵바 피드백)
- 가이드 하단 "이 경조사 기록하기" → 빠른 입력 프리필 (콘텐츠→장부 전환 동선)
- 액수 기준 하단 고지: "일반적인 기준이며 관계·지역에 따라 다를 수 있습니다"

### 5.4 통계
- 월별 받음/줌 바 차트, 관계별 파이, 누적 순액
- 기간 선택 (올해/전체/커스텀)

### 설정 (탭 아님, 홈 우상단)
- 앱 잠금 on/off (생체인증 + PIN), CSV 내보내기, 답례 알림 기본값, 오픈소스 라이선스

## 6. 마일스톤 (2주)

| Day | 작업 | 완료 기준 |
|---|---|---|
| D1 | 프로젝트 세팅, 테마, 라우팅, Drift 스키마+DAO | 유닛테스트로 CRUD 통과 |
| D2~3 | 빠른 입력 플로우 + 기록 리스트 | 10초 입력 달성 |
| D4 | 지인 관리 + 지인별 상세(차액/답례 토글) | |
| D5 | 검색/필터 | |
| D6~7 | 홈 대시보드 + 통계 | |
| D8 | 예절 가이드 (JSON 파싱, 복사, 프리필 동선) | |
| D9 | 답례 알림, CSV 내보내기 | |
| D10 | 앱 잠금(생체인증), 다크모드 점검 | |
| D11 | 아이콘/스플래시, 스토어 스크린샷 5장 | |
| D12 | 스토어 문구(ASO), 개인정보처리방침 페이지(수집 안 함 고지) | |
| D13~14 | 양 스토어 심사 제출 | |

## 7. 비기능 요구사항

- 완전 오프라인 동작, 네트워크 권한 미사용 (iOS 개인정보 라벨 "수집 안 함")
- 금액 입력 시 천단위 콤마, 한글 금액 병기 (예: 100,000 → 십만원)
- 큰 글씨 모드 대응 (textScaleFactor 1.3까지 레이아웃 안 깨짐)
- 앱 크기 30MB 이하 목표

## 8. Codex 리뷰 요청 포인트

1. **스키마**: events 없이 transaction.date만으로 충분한 케이스가 많은데, events 테이블 분리가 과설계인지 (vs transaction에 eventType 인라인)
2. **빠른 입력 3스텝**의 상태 관리 구조 — Riverpod로 멀티스텝 폼 다루는 베스트 프랙티스
3. SQLCipher 도입 비용 대비 효용 — 로컬 전용 앱에서 OS 샌드박스 + 앱 잠금만으로 충분한가
4. 복권 앱 재활용을 위한 shared/db 추상화 수준 — 지금부터 분리 vs 출시 후 리팩토링
5. 답례 배지 로직: 차액 기반이 맞는지, 건별 매칭(이 거래에 대한 답례) 방식이 나은지

## 9. 디자인 이미지 생성 프롬프트

### 9.1 앱 아이콘 (로고)

```
Minimal flat app icon for a Korean gift-money ledger app called "Ogan Maeum"
(exchanged hearts). A traditional Korean white envelope (bongtu) slightly
tilted, with a small warm red-orange heart emerging from its opening.
Soft ivory/hanji-paper background, single subtle shadow, rounded square
iOS app icon format. Warm minimalism, two or three colors max
(ivory, charcoal line, warm red-orange accent). No text, no gradients,
no 3D, centered composition, crisp vector style.
```

### 9.2 브랜드 컨셉 이미지 (스토어/랜딩용)

```
Warm minimal brand concept illustration for a Korean app about gift money
etiquette (weddings and funerals). Two hands gently exchanging a white
Korean envelope tied with a traditional maedeup knot thread, hanji paper
texture background in soft ivory, subtle warm red-orange and muted
charcoal palette. Flat illustration, generous negative space, calm and
respectful mood, no faces, no text. 16:9 composition.
```

### 9.3 스토어 스크린샷 배경 프레임

```
Set of clean app store screenshot background frames, soft ivory hanji
paper texture with very subtle warm gradient, minimal Korean traditional
pattern (thin line dancheong-inspired border) at top corner only,
large empty center area for phone mockup, warm red-orange accent color,
flat minimal style, 1290x2796 portrait.
```

### 프롬프트 사용 팁
- 아이콘은 "no text" 유지 — 텍스트는 생성이 아니라 벡터로 후작업
- 색 팔레트 고정값 제안: 아이보리 `#FAF6EF`, 차콜 `#3A3A3A`, 웜레드 `#E8604C`
- 결과물 중 봉투 실루엣이 명확한 것 선택 (작은 사이즈에서 식별성이 아이콘의 전부)
