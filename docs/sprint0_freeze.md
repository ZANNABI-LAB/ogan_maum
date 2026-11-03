# 오간마음 — Sprint 0 Freeze 산출물 (FINAL)

> ⚠️ **개정 필요 (2026-11-03)** — 기획 v2 로 Freeze 를 다시 연다. 개정 항목은 `docs/product/plan-v2.md` §9. 개정 전까지 이 문서를 근거로 새 구현을 시작하지 않는다.

> v1.1 반례 검토 완료 + 코덱스 최종 승인(98/100) 반영. 규칙 공백 2건 보완(INV-1, INV-9), 결정 확정(method 컬럼 제거, uid 미도입), INV-11 결과 타입화.
> **본 문서가 Sprint 0의 최종 기준이다. 추가 설계 토론 없이 구현한다.**

---

## 1. 최종 Drift Table 정의

```dart
// shared/db/tables.dart

class PersonGroups extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get name => text().withLength(min: 1)();
  TextColumn get relationType => text()(); // NOT NULL — stable code
  IntColumn get sortOrder => integer().withDefault(const Constant(0))();
  IntColumn get createdAt => integer()(); // epoch millis UTC
  IntColumn get updatedAt => integer()();
}

class Persons extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get name => text().withLength(min: 1)(); // NOT UNIQUE — 동명이인 허용
  TextColumn get relationType => text()();
  IntColumn get groupId => integer()
      .nullable()
      .references(PersonGroups, #id, onDelete: KeyAction.setNull)();
  TextColumn get memo => text().nullable()();
  IntColumn get createdAt => integer()();
  IntColumn get updatedAt => integer()();
}

class Events extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get relatedPersonId => integer()
      .nullable()
      .references(Persons, #id, onDelete: KeyAction.restrict)();
  TextColumn get type => text()(); // stable code
  TextColumn get title => text().withLength(min: 1)();
  TextColumn get date => text()(); // yyyy-MM-dd
  TextColumn get time => text().nullable()(); // HH:mm
  TextColumn get place => text().nullable()();
  TextColumn get memo => text().nullable()();
  IntColumn get createdAt => integer()();
  IntColumn get updatedAt => integer()();
}

class Transactions extends Table {
  IntColumn get id => integer().autoIncrement()();
  IntColumn get personId => integer()
      .references(Persons, #id, onDelete: KeyAction.restrict)();
  IntColumn get eventId => integer()
      .nullable()
      .references(Events, #id, onDelete: KeyAction.setNull)();
  TextColumn get occasionType => text()(); // eventId 있으면 Event.type 복사본
  TextColumn get direction => text()(); // received | given
  IntColumn get amount =>
      integer().check(amount.isBiggerThanValue(0))(); // amount > 0
  TextColumn get occurredOn => text()(); // yyyy-MM-dd
  TextColumn get followUpStatus => text()(); // none | pending | done
  TextColumn get memo => text().nullable()();
  IntColumn get createdAt => integer()();
  IntColumn get updatedAt => integer()();
}
```

- `method` 컬럼: **생성하지 않음** (Option B 확정). 필요 시 이후 nullable 추가.
- `uid`: **생성하지 않음.** 백업/동기화 스프린트에서 migration + backfill.

### Stable Code 정의 (DB contract — Dart enum name과 분리)

```text
relationType : family | relative | friend | work | acquaintance | other
occasionType : wedding | funeral | first_birthday | birthday_60 | opening | other
direction    : received | given
followUpStatus: none | pending | done
```

각 enum에 `String get dbCode` / `fromDbCode()` 매퍼를 두고 Drift TypeConverter로 연결한다. `enumValue.name` 직접 저장 금지.

---

## 2. FK 및 Index

### FK (스키마 레벨)
| FK | onDelete |
|---|---|
| persons.groupId → person_groups.id | SET NULL |
| transactions.personId → persons.id | RESTRICT |
| transactions.eventId → events.id | SET NULL |
| events.relatedPersonId → persons.id | RESTRICT |

`beforeOpen`에서 `PRAGMA foreign_keys = ON` 필수 (SQLite 기본 OFF).

### Index (Sprint 0)
```sql
CREATE INDEX idx_tx_occurred            ON transactions (occurred_on);
CREATE INDEX idx_tx_person_occurred     ON transactions (person_id, occurred_on);
CREATE INDEX idx_tx_person_occ_occurred ON transactions (person_id, occasion_type, occurred_on);
CREATE INDEX idx_tx_event               ON transactions (event_id);
CREATE INDEX idx_person_group           ON persons (group_id);
```

추가 인덱스(events.date 등)는 해당 Sprint의 migration에서.

---

## 3. Repository Invariant 목록 (구현 + 테스트 대상)

**INV-1** `PersonGroup.relationType`은 생성 후 **수정 불가** (이름·sortOrder만 수정 가능) — v1.1 공백 보완
**INV-2** `person.groupId != null` → `person.relationType == group.relationType` (그룹 지정 시 person 쪽을 동기화, 단일 DB transaction)
**INV-3** `person.relationType` 변경 시 비호환 그룹이면 `groupId = null`
**INV-4** `tx.eventId != null` → `tx.occasionType == event.type` (연결 시 복사)
**INV-5** `event.type` 변경 → 연결된 모든 tx.occasionType atomic 갱신
**INV-6** 연결 해제(eventId → null) 시 occasionType 유지
**INV-7** eventId 있는 tx의 occasionType 직접 변경 거부 (Event.type 수정 유도)
**INV-8** `event.relatedPersonId != null` → 연결되는 모든 tx는 `tx.personId == relatedPersonId` (연결 시점 검증, 위반 시 거부)
**INV-9** 연결 tx와 불일치가 발생하는 `relatedPersonId` 변경은 거부 (연결 해제 먼저 유도) — v1.1 공백 보완
**INV-10** followUpStatus 기본값: received → pending, given → none. direction 수정 시 재적용
**INV-11** Person 삭제: tx 또는 event 참조 존재 시 거부. Repository는 UI 문자열이 아닌 **결과 타입**만 반환하고, 안내 문구는 Presentation에서 생성한다 (다국어/문구 정책과 Domain 분리):

```dart
sealed class DeletePersonResult {}

class DeletePersonSuccess extends DeletePersonResult {}

class DeletePersonBlocked extends DeletePersonResult {
  final int transactionCount;
  final int eventCount;
  DeletePersonBlocked(this.transactionCount, this.eventCount);
}
```

---

## 4. Migration Strategy

- `schemaVersion = 1`
- `onCreate`: `createAll()` + 인덱스 생성
- `beforeOpen`: `PRAGMA foreign_keys = ON`, (debug) `validateDatabaseSchema()`
- 이후 버전업은 `Migrator.stepByStep` 사용, 각 단계는 전진만(다운그레이드 미지원)
- drift_dev `schema` 툴로 v1 스키마 스냅샷 export → 마이그레이션 테스트의 기준으로 저장
- 예약된 향후 migration 메모(구현 금지): `method nullable 추가`, `uid backfill`, `events.date index`, `externalCalendarId`

---

## 5. Sprint 0 Unit Test 목록

**CRUD/기본**
1. 각 테이블 insert/select/update/delete 왕복
2. 앱 재시작(커넥션 재오픈) 후 데이터 유지
3. amount <= 0 insert 실패
4. 동명이인 Person 2건 insert 성공

**Invariant**
5. 그룹 지정 시 person.relationType 동기화 (INV-2)
6. relationType 변경 시 비호환 그룹 해제 (INV-3)
7. 그룹 relationType 수정 시도 → 거부 (INV-1)
8. Event 연결 시 occasionType 복사 (INV-4)
9. Event.type 변경 → 연결 tx 전체 갱신, 부분 실패 시 롤백 (INV-5, atomic)
10. 연결 해제 후 occasionType 유지 (INV-6)
11. 연결 상태 occasionType 직접 변경 거부 (INV-7)
12. relatedPersonId 불일치 tx 연결 거부 (INV-8)
13. 연결 tx 존재 시 relatedPersonId 변경 거부 (INV-9)
14. relatedPersonId=null 이벤트에 여러 사람 tx 연결 허용 (내 결혼식 케이스)
15. followUpStatus 기본값 및 direction 수정 시 재적용 (INV-10)

**FK/삭제**
16. Person 삭제 시 DeletePersonBlocked(transactionCount, eventCount) 반환 검증 (INV-11)
17. Group 삭제 → person.groupId null, relationType 유지
18. Event 삭제 → tx.eventId null, 거래 사실 유지

**Migration/기타**
19. v1 스키마 스냅샷 검증 (validateDatabaseSchema)
20. stable code 매퍼 왕복 (enum ↔ dbCode) 전수 테스트

---

## 6. 구현 규율 (Freeze 이후 지킬 것)

**R-1. 계층 규율** — Feature 코드에서 Table/DAO 직접 접근 금지. 반드시 `Presentation → Application/Notifier → Repository → DAO → Drift` 경로만 사용한다. INV-1~11이 전부 Repository에 있으므로, `database.update(persons)...`를 Feature에서 직접 호출하는 순간 모든 invariant가 무력화된다.

**R-2. 날짜/시간 검증은 Repository 진입점에서** — occurredOn/date/time은 TEXT라 `2026-99-88`, `25:90` 같은 값이 이론상 들어갈 수 있다. DB CHECK는 만들지 않고, LocalDate/LocalTime 개념의 parser/validator를 하나 두어 잘못된 값이 저장 경로를 통과하지 못하게 한다.

**R-3. invariant 테스트는 Repository public API 기준** — DB 결과 확인이 아니라 실제 API 호출로 검증한다. 특히 INV-5는 `changeEventType()` 실행 + 의도적 중간 실패 주입 → Event와 연결 Tx 전체(예: 1+3건)가 모두 롤백되는지까지 확인한다.

**Sprint 0 범위 방어**: 구현 중 UUID, Tag, soft delete, sync metadata, historical relation 등의 "더 좋은 방법" 제안은 거절한다. 이번 Sprint의 성공 기준은 아름다운 스키마가 아니라 **Freeze한 11개 invariant가 실제 코드와 테스트에서 깨지지 않는 것**이다.

---

## 7. 남아 있는 Blocker — 없음. FROZEN.

v1.1 규칙 공백 2건(INV-1, INV-9) 보완 완료, method/uid 결정 확정, 코덱스 최종 승인 반영(INV-11 결과 타입화). **이후 설계 토론 없이 아래 순서로 닫는다:**

```text
Drift Table 구현 → DAO → Repository invariant → 테스트 20개 전체 PASS
→ Schema snapshot → Sprint 0 DONE → Sprint 1 (10초 빠른 입력)
```

Sprint 1부터는 아키텍처가 아니라 `사람 선택 → 결혼 → 보냄 → 10만원 → 저장`이 손에서 얼마나 빠르고 자연스러운가에 시간을 쓴다.
