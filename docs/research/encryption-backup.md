# 암호화·백업 기술 조사 (2026-11-03)

> AI 조사 에이전트가 공식 문서·패키지 문서·이슈 트래커에서 수집. "추정"은 공식 확인 안 됨.

## 결론: Keystore/Keychain 에 둔 DB 키는 기기 변경 시 따라오지 않는다

**Android — 거의 확실히 실패**
- Auto Backup 은 SQLite 파일·SharedPreferences 를 백업 (앱당 25MB, Android 9+ 화면잠금 시 E2E) https://developer.android.com/identity/data/autobackup
- Keystore 키는 non-exportable, 보안 하드웨어에 묶임 → 백업·이전 안 됨 https://developer.android.com/privacy-and-security/keystore
- flutter_secure_storage 는 감싼 키를 prefs 에 저장 → 복원 후 `Failed to unwrap key` 등. README 가 백업 제외 권고 https://pub.dev/packages/flutter_secure_storage · https://github.com/mogol/flutter_secure_storage/issues/248

**iOS — 복원 경로에 따라 다름**
- 앱 데이터는 iCloud 백업 포함. iCloud 백업의 키체인은 기기 UID 파생 키로 암호화돼 같은 기기로만 복원 https://support.apple.com/guide/security/security-of-icloud-backup-sec2c21e7f49/web · https://developer.apple.com/forums/thread/106493
- 암호화된 Finder 백업은 ThisDeviceOnly 가 아닌 항목을 옮김 https://support.apple.com/guide/security/keybags-for-data-protection-sec6483d5760/web
- Quick Start 는 키체인을 옮긴다는 보고 (추정)
- flutter_secure_storage iOS 기본값 `synchronizable: false`

## 기술 현황
- **`sqlcipher_flutter_libs` 지원 종료 (0.7.0+eol)** https://pub.dev/packages/sqlcipher_flutter_libs
- Drift 는 sqlite3 3.x 빌드 훅의 `sqlite3mc`(SQLite3MultipleCiphers) 권장, `PRAGMA key` https://drift.simonbinder.eu/platforms/encryption/
- SQLCipher 오버헤드 5~15% https://www.zetetic.net/sqlcipher/performance

## 위협 모델
- Android FBE·iOS Data Protection 이 기기 잠금에 묶임 https://source.android.com/docs/security/features/encryption/file-based
- OWASP MASVS-STORAGE 는 DB 암호화를 강제하지 않음 https://raw.githubusercontent.com/OWASP/masvs/master/Document/05-MASVS-STORAGE.md
- 추가 DB 암호화가 막는 것: 루팅·포렌식 기기에서의 파일 추출, 평문 백업 유출 (추정). 키가 같은 기기에 있으면 이득은 제한적

## 옵션
| 옵션 | 기기 변경 복원 | 보안 | 비용 | UX |
|---|---|---|---|---|
| A DB 암호화 + Keystore/Keychain 키 | 나쁨 | 중 | 중 | 복원 후 "데이터 사라짐" 위험 |
| **B 암호화 없음 + OS 보호 + 앱 잠금** | **좋음** | OS 의존 | 낮음 | 가장 좋음 |
| C sqlite3mc + 비밀번호 파생 키 | 좋음 | 높음 | 중상 | 비밀번호 분실 = 영구 손실 |
| D1 DEK 를 Block Store / 동기화 키체인에 | 중~좋음 | 중 | 중상 | 경계 사례 테스트 어려움 |

## 채택 (D-07): B + 비밀번호 암호화 `.ogan` 백업 파일
- `VACUUM INTO` 스냅샷 → Argon2id 등 KDF + AES-GCM 암호화
- 저장: `file_picker` saveFile(Android SAF, iOS 문서 선택기)로 사용자가 Drive/iCloud Drive 폴더 선택 https://pub.dev/packages/file_picker — Drive API·OAuth 불필요
- 사용자가 직접 올린 백업은 개발자 수집 아님 → "수집 없음" 유지 https://support.google.com/googleplay/android-developer/answer/10787469
- 주의: DB 25MB 초과 시 Android 클라우드 백업 중단
