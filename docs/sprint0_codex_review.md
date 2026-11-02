# 오간마음 — Sprint 0 결정사항 (코덱스 최종 점검 요청)

> 플랜 v2 기준, 구현 착수 전 확정이 필요한 스키마/규칙 6건.
> 각 항목의 [결정]이 타당한지, 놓친 엣지 케이스가 있는지 점검 바랍니다.

---

## 1. relationType 이중 존재 문제 (Person / PersonGroup)

**문제**: Person과 PersonGroup 양쪽에 relationType이 있어 `person=친구, group=직장` 같은 모순 데이터 가능. Sprint 5 통계 드릴다운(관계 → 그룹)은 "그룹이 관계 아래 중첩"을 전제하지만 스키마가 이를 보장하지 않음.

**[결정]**
- 통계 1단계 축은 `person.relationType`, 2단계 축은 `person.groupId`
- 사람에게 그룹 지정 시, 그룹에 relationType이 있으면 사람의 relationType을 그룹 값으로 동기화
- 동기화는 Repository 레벨 invariant로 구현 + 유닛테스트로 보장 (DB 트리거 사용 안 함)

**점검 요청**: 그룹의 relationType이 nullable인데, null 그룹에 속한 사람의 드릴다운 처리 방식이 이 규칙으로 충분한가?

---

## 2. Transaction.occasionType vs Event.type 중복

**문제**: Event 연결 시 두 값이 어긋날 수 있음 (거래=wedding, 이벤트=funeral). Sprint 7 Priority 1 매칭("같은 사람+같은 경조사")은 Transaction.occasionType 기준이므로 불일치 시 컨텍스트 기능이 오작동.

**[결정]**
- `eventId != null`인 Transaction의 occasionType은 event.type의 **복사본**으로 정의
- Event.type 수정 시 연결된 모든 Transaction.occasionType을 Repository에서 함께 갱신
- 이 invariant를 Sprint 0 테스트 스위트에 포함

---

## 3. FK 삭제 정책

**[결정]**
| 삭제 대상 | 정책 | 근거 |
|---|---|---|
| Person (거래 있음) | RESTRICT — 막고 안내 | 기록 보존이 제품 철학. CASCADE 금지 |
| PersonGroup | person.groupId → SET NULL | 그룹은 라벨일 뿐 |
| Event | transaction.eventId → SET NULL | 거래(돈의 사실)는 남김 |

**점검 요청**: Person RESTRICT 시 "거래 포함 전체 삭제" 옵션을 UI에서 제공할지 (제공한다면 명시적 2단계 확인 후 CASCADE 수동 실행), 아예 막을지.

---

## 4. 날짜 저장 형식

**문제**: 경조사 날짜는 timezone 없는 "그 날". DateTime(UTC) 저장 시 자정 경계 하루 밀림 버그 위험.

**[결정]**
- `transaction.occurredAt`: date-only, TEXT `yyyy-MM-dd` 저장
- `event.date`: 동일하게 date-only + `event.time`: nullable TEXT `HH:mm` 분리 유지
- `createdAt/updatedAt`: epoch millis (UTC)

---

## 5. Sprint 7 대비 인덱스 & 집계 계산 위치

**[결정]**
- 인덱스: `transactions(personId, occasionType, occurredAt)`, `transactions(eventId)`, `persons(groupId)`
- 중앙값: SQLite median 미지원 → 금액 리스트 조회 후 Dart에서 계산 (개인 장부 규모에서 성능 문제 없음, SQL로 풀지 않는다)
- 집계값 DB 저장 금지 원칙(플랜 11장) 유지

---

## 6. Enum 저장 방식

**[결정]**: 모든 enum(relationType, occasionType, direction, method, followUpStatus)은 TEXT 저장. int 매핑 금지 — 값 추가 시 마이그레이션 불필요, 백업 파일 가독성 확보.

**메모(구현하지 않음)**: Sprint 9에서 `event.externalCalendarId nullable` 추가 예정 — 마이그레이션 목록에만 기록.

---

## 최종 확인 질문

1. 위 6건 확정 시 Sprint 0 스키마에 남는 리스크가 있는가?
2. Sprint 4~10 로드맵 기준으로 지금 추가해야 할 컬럼/인덱스가 더 있는가? (원칙: 미래 기능 선구현 금지, 단 마이그레이션이 고통스러운 구조 결정만 예외)
3. followUpStatus의 상태 전이(none→pending→done)에 트랜잭션 생성 시 기본값 규칙이 필요한가? (현재안: direction=received면 pending, given이면 none)
