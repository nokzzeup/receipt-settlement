# 프로젝트 기준 문서

팀 전체가 같이 보는 기준. 범위·규칙·모델이 바뀌면 이 문서부터 고친다.
실행 방법은 [README](../README.md), 지금까지 내린 설계 결정은 [DECISIONS](DECISIONS.md).

## 개요

- **이름**: 영수증 이미지 기반 비(非)법인카드 조직 지출 정산 시스템
- **대상**: 법인카드가 없는 학생회·동아리·소규모 팀. 구성원이 개인 카드로 먼저 결제하고, 나중에 총무가 정산해 돌려주는 구조
- **핵심 흐름**: 조직 생성/참여 → 영수증 촬영 → OCR 인식 → 결과 확인·수정 → 품목별 계정 자동 분류 → 승인 → 결제자별 환급 집계·완료 처리 → 리포트/엑셀
- **차별점**: 법인카드 불필요 / 품목 단위 처리(한 영수증에 섞인 지출 분리) / 선결제·환급 중심 / 무비용 로컬 실행
- **기간**: 2026.09 ~ 12 (15주)

## 기능 범위

**필수**
1. 조직·계정: 회원가입/로그인, 조직 생성, 초대 코드로 참여, 역할(TREASURER 총무 / APPROVER 승인자 / MEMBER 구성원), 계정과목(=예산 항목) 등록
2. 등록·인식: PWA 카메라 촬영, 이미지 전처리 + OCR, 인식 결과 확인·수정, 원본 이미지 보관, 중복 영수증 감지
3. 품목 분류: 품목명 → 계정과목 자동 매핑, 사용자 수정 이력으로 매핑 규칙 보강
4. 정산·예산: 결제자 지정, 구성원별 환급 대상 금액 집계, 환급 완료 처리, 계정별 집행액·잔액, 예산 초과 경고
5. 결재·출력: 제출 → 승인/반려(사유 기록), 기간별 리포트, 엑셀 내보내기

**여력 시 확장**: 승인·반려 알림(앱 내 알림 목록), 기간 마감(결산 잠금), 활동 로그

**범위 제외**: 실제 송금, 카드사 연동, 세금계산서, 외부 회계 시스템 연동, 유료 API, 네이티브 앱

## 기술 스택 / 제약

| 영역 | 선택 |
|---|---|
| 프론트 | React + Vite + TypeScript, react-router, TanStack Query, vite-plugin-pwa. 모바일 우선 UI. 촬영은 `<input type="file" accept="image/*" capture="environment">` |
| 백엔드 | Python 3.13(3.12 가능), FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest |
| DB | SQLite (`backend/data/app.db`). `DATABASE_URL`만 바꾸면 PostgreSQL로 전환 가능 |
| OCR | OpenCV 전처리 + PaddleOCR(한국어), 로컬 실행 |
| 이미지 저장 | 로컬 파일시스템(`backend/storage/`), 외부 스토리지 사용 안 함 |
| 인증 | 1차 이메일/비밀번호 + JWT. 카카오 로그인은 2차에 같은 인증 구조에 추가 |
| 실행 | `npm run setup`(처음 한 번) → `npm run dev`(백엔드 + 프론트 동시) |

예산 규정상 구독료·유료 API·유료 호스팅 사용 불가 → 모든 구성요소는 무료/오픈소스.

## 코딩 규칙

- 금액은 원 단위 정수(`int`)로만 다룬다. float 금지 (DB 계층에서도 강제됨)
- 시간은 timezone-aware로 저장하고, 표시는 Asia/Seoul 기준 (시간대 없는 값은 DB 저장 시 에러)
- API는 `/api/v1` 아래 REST. 프론트 타입은 FastAPI OpenAPI 스키마에서 생성한다 (`npm run gen:api`)
- 권한 체크는 항상 서버에서 "조직 멤버십 + 역할" 기준으로 한다. 다른 조직 데이터 접근 차단
- OCR 원문을 저장하기 전에 카드번호 패턴은 마스킹한다
- 비밀값은 `.env`로 관리하고 커밋하지 않는다. `.env.example`을 유지한다
- 정산 엔진(환급 집계, 잔액 계산)은 반드시 pytest 단위 테스트를 함께 작성한다
- `backend/alembic.ini`, `backend/requirements*.txt`에는 한글을 쓰지 않는다 (한국어 Windows에서 깨짐, 테스트로 검사)

## 도메인 모델 (현재 구현 기준)

| 모델 | 주요 필드 |
|---|---|
| User | email, password_hash, name |
| Organization | name, invite_code(재발급 가능), created_by_user_id |
| Membership | user, organization, role(TREASURER/APPROVER/MEMBER) |
| Category | organization, name, budget_amount(nullable) — 계정과목 겸 예산 항목 |
| Receipt | organization, uploader(Membership), image_path, image_hash, ocr_raw(JSON, 마스킹 후), store_name, paid_at, total_amount |
| Expense | organization, receipt(1:1), payer(Membership), status(DRAFT/SUBMITTED/APPROVED/REJECTED), reject_reason, reimbursed_at, reimbursed_by(Membership) |
| ExpenseItem | expense, name, quantity, unit_price, amount, category, category_source(AUTO/MANUAL) |
| MappingRule | organization(NULL=전역 규칙), keyword, category(조직 규칙) 또는 category_name(전역 규칙), hit_count |
| ApprovalLog | expense, actor(Membership), action(SUBMIT/APPROVE/REJECT/REIMBURSE), comment, created_at |

- 중복 감지: image_hash 유사도 또는 (store_name, paid_at, total_amount) 일치 시 경고
- 지출 금액은 별도 컬럼 없이 품목(ExpenseItem.amount) 합계로 계산
- 자세한 이유는 [DECISIONS](DECISIONS.md)

## OCR 모듈 경계 (병렬 작업용 계약 — 합의 없이 변경 금지)

- `backend/app/ocr/` (김도현): 전처리 + OCR 엔진
  - `OcrEngine.recognize(image_bytes) -> OcrRawResult`
  - `OcrRawResult = { engine: str, lines: [{ text: str, confidence: float, bbox: [[x,y] x 4] }] }`
  - `MockOcrEngine`(고정 샘플)으로 먼저 개발, `.env`의 `OCR_ENGINE=mock|paddle`로 전환
- `backend/app/parsing/` (이성민): `OcrRawResult -> ReceiptFields`
  - `ReceiptFields = { store_name, paid_at, total_amount, items: [{ name, quantity, unit_price, amount }] }`

## 디렉토리 / 담당

| 경로 | 내용 | 담당 |
|---|---|---|
| `frontend/` | React PWA | 신율겸 |
| `backend/app/api/` | 라우터 | 이성민 |
| `backend/app/models/`, `backend/app/db/` | 모델, 세션, 마이그레이션 | 김도현 |
| `backend/app/ocr/` | 전처리·OCR 엔진 | 김도현 |
| `backend/app/parsing/` | 영수증 필드 파싱 | 이성민 |
| `backend/app/classify/` | 품목→계정 분류 | 이성민 |
| `backend/app/settlement/` | 정산 엔진 | 이성민 |
| `backend/tests/` | 테스트 | 전원 |
| `dataset/` | 테스트 영수증 이미지 + 정답 라벨(JSON) | 김도현 |
| `scripts/` | 실행 스크립트, 정확도 측정 등 유틸 | — |

## 팀

- **이성민(팀장)**: 시스템 설계, 백엔드 API, 파싱·분류, 정산 엔진, 정확도 측정
- **김도현**: DB 설계·구축, OCR 파이프라인, 영수증 수집·라벨링
- **신율겸**: 프론트엔드 PWA UI/UX

## 개발 단계

| 단계 | 내용 | 상태 |
|---|---|---|
| 0 | 뼈대: 레포 구조, 실행 명령, 헬스체크, 모델·첫 마이그레이션, Mock OCR, 프론트 라우팅·빈 화면 | 완료 |
| 1 | 인증, 조직 생성, 초대 코드 참여, 역할 권한 | |
| 2 | 영수증 업로드 → Mock OCR → 확인·수정 화면 → 지출 등록 | |
| 3 | 실제 OCR(전처리 + PaddleOCR) + 파싱 | |
| 4 | 품목→계정 자동 분류 + 수정 학습 | |
| 5 | 승인 흐름, 정산 엔진(환급 집계·완료), 예산 잔액 | |
| 6 | 리포트·엑셀, 중복 감지 | |
| 7 | 정확도 측정 스크립트, 실사용 테스트 대응 | |
