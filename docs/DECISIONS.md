# 설계 결정 기록

"왜 이렇게 했지?"가 궁금할 때 보는 문서. 결정을 바꾸면 여기에 날짜와 이유를 추가한다.

## 0단계 (2026-10-02 ~ 10-04)

### DB: PostgreSQL + Docker → SQLite
- 처음엔 Docker로 PostgreSQL을 띄웠지만, Windows에서 Docker Desktop 첫 세팅(WSL·가상화·엔진 시작)이 팀원마다 막힐 위험이 커서 뺐다
- 동아리 하나 규모에서는 PostgreSQL이어야만 하는 기능이 없고, "무비용 로컬 실행"이라는 차별점에도 파일 하나짜리 DB가 더 맞는다
- 특정 DB 전용 기능(JSONB 등)은 쓰지 않는다 → `DATABASE_URL`만 바꾸면 PostgreSQL로 돌아간다 (같은 마이그레이션·테스트가 PostgreSQL 16에서 통과하는 것 확인)

### SQLite의 약점은 공통 코드에서 막음 (`backend/app/db/`)
| 약점 | 대응 |
|---|---|
| 시간대 정보를 조용히 버림 (14:32 KST가 그냥 14:32로 저장) | `UTCDateTime` 타입: 시간대 없는 값은 저장 시 에러, UTC로 저장하고 읽을 때 UTC를 붙여서 반환 |
| INTEGER 컬럼에 소수도 그냥 저장됨 | `StrictInteger` 타입: 금액·수량에 int가 아니면 저장 시 에러 |
| 외래키 검사가 기본으로 꺼져 있음 | 연결할 때마다 `PRAGMA foreign_keys=ON` |
| 파이썬 드라이버의 옛날 트랜잭션 방식 (SAVEPOINT 오동작) | SQLAlchemy 공식 권장 방식으로 BEGIN을 직접 관리 |
| 읽기·쓰기가 서로 막음 | WAL 모드 |

- 마이그레이션은 batch 모드(테이블을 새로 만들어 데이터를 옮김). 이때는 일부러 외래키 검사를 끈다 — 켜두면 테이블을 지우는 순간 CASCADE로 자식 데이터(지출 품목 등)가 같이 지워진다
- 위 동작은 `backend/tests/test_db_rules.py`가 검사한다

### Python 3.12/3.13 고정 (3.14 이상 불가)
- 3단계에 쓸 PaddlePaddle(3.3.1)·PaddleOCR(3.7.0)가 Windows·Mac용 Python 3.14 설치 파일을 아직 내놓지 않음 (2026-10-04 확인)
- `npm run setup`이 3.12/3.13이 아니면 이유를 말하고 멈춘다

### 한국어 Windows 인코딩 주의
- Alembic은 `alembic.ini`를 UTF-8이 아니라 OS 인코딩(한국어 Windows는 cp949)으로 읽는다. 한글 주석 하나로 `npm run setup`이 실패했었다
- `alembic.ini`, `requirements*.txt`, `script.py.mako`는 영어로만 쓴다 (`backend/tests/test_repo_files.py`가 검사)

### 도메인 모델 세부 결정
- **행위자는 전부 Membership을 가리킴**: 결제자·업로더·승인 처리자·환급 처리자 컬럼은 `*_membership_id`. 같은 사람도 조직마다 역할이 다르고, `user.id`를 잘못 넣는 실수를 막기 위해서. 조직 생성자만 `created_by_user_id`
- **지출 금액 컬럼 없음**: 품목 금액 합계로 계산 (값이 두 군데 있으면 어긋남). 개인 지출 품목을 빼면 환급액이 자동으로 줄어든다
- **영수증 : 지출 = 1 : 1**: `Expense.receipt_id`는 필수 + 유일
- **DB 제약으로 막는 것**: 환급 정보(일시·처리자)는 함께 있어야 하고 승인(APPROVED) 상태에서만 가능, 수량 > 0, 예산 ≥ 0
- **Enum은 문자열 + CHECK 제약**: DB 고유 ENUM은 값 변경 시 마이그레이션이 번거로움
- **MappingRule 전역 규칙**: 계정과목이 조직마다 따로 있어서 전역 규칙은 특정 계정과목 ID를 가리킬 수 없다 → 이름(`category_name`, 예: "식비")으로 저장하고, 분류할 때 그 조직의 같은 이름 계정과목에 매칭. 조직 규칙은 `category_id`. CHECK 제약으로 둘 중 하나만 허용
- **삭제 정책**: 자동 삭제(CASCADE)는 지출 → 품목·결재 이력, 계정과목 → 매핑 규칙만. 조직·멤버십·영수증·사용 중인 계정과목은 참조하는 데이터가 있으면 삭제가 막힌다 (재무 기록 보존). 조직 삭제·탈퇴가 필요해지면 soft delete로
- **같은 조직 데이터끼리만 연결되는지**(영수증·결제자·계정과목)는 DB가 보장하지 않으므로 API/서비스 계층에서 검증한다

### 실행 구조
- 루트 `package.json`의 npm 명령 하나로 백엔드와 프론트를 같이 실행 (`concurrently`, Ctrl+C 한 번에 둘 다 종료)
- 더블클릭 실행 파일(`start-windows.bat`, `start-mac.command`): 패키지 목록(requirements·package-lock)의 지문을 `backend/.venv/setup-stamp.txt`에 남겨두고, 바뀌었으면 실행 전에 setup을 자동으로 다시 한다 → `git pull` 후에도 더블클릭만 하면 됨
- `start-windows.bat`은 영어로만 쓴다 (cmd.exe가 OS 인코딩으로 읽음). 한글 안내는 Node 스크립트(`scripts/launch.mjs`)가 출력
- Vite는 `strictPort`: 5173이 이미 쓰이면 다른 포트로 바꾸지 않고 에러 → 주소가 항상 같음
- 프론트는 `/api` 요청을 Vite 프록시로 백엔드(127.0.0.1:8000)에 넘긴다 → CORS 불필요, 폰에서 접속해도 그대로 동작

## 아직 정할 것

- [ ] **예산 기간**: 학기/연 단위 개념이 없어서 지금은 잔액이 전체 누적으로 계산됨 → 5단계 전에 결정
- [ ] **영수증 없는 지출**(계좌이체·현금) 허용 여부 → 허용하면 `Expense.receipt_id`를 nullable로
- [ ] **MappingRule 전역 규칙**: 지금 방식(DB에 이름으로 저장) 유지 vs 코드 기본값으로 두기
