# 영수증 정산 (가칭) — 팀 재(무)재(경)이야

법인카드 없는 학생회·동아리·소규모 팀을 위한 영수증 이미지 기반 지출 정산 PWA.
영수증 촬영 → OCR → 확인·수정 → 품목별 계정 분류 → 승인 → 결제자별 환급 집계.

> 📄 범위·규칙·모델: [docs/PROJECT.md](docs/PROJECT.md) · 설계 결정과 이유: [docs/DECISIONS.md](docs/DECISIONS.md)

**지금 되는 것 (2단계까지)**: 회원가입·로그인 → 조직 만들기/초대 코드로 참여 → 역할·계정과목(예산) 관리 →
영수증 촬영·업로드 → 인식 결과(지금은 Mock OCR 고정 샘플) 확인·수정 → 임시 저장 / 제출 → 지출 목록

| 구성 | 기술 |
|---|---|
| frontend | React 19 + Vite 8 + TypeScript, react-router 8, TanStack Query 5, vite-plugin-pwa |
| backend | Python 3.13, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest |
| DB | SQLite (`backend/data/app.db`, 설치 불필요) — 설정 한 줄로 PostgreSQL 전환 가능 |

---

## 처음 한 번: 설치

**1. Git** — https://git-scm.com (Windows 설치 옵션은 전부 기본값)

**2. Node.js 24 LTS** — https://nodejs.org

**3. Python 3.13** — https://www.python.org/downloads/
- 다운로드 페이지 맨 위 버튼은 최신 버전(3.14 이상)이니 **목록에서 3.13.x를 골라서** 받을 것
  (3.14 이상은 3단계에 쓸 PaddleOCR가 아직 지원하지 않음. 3.12는 가능)
- Windows: 설치 첫 화면에서 **"Add python.exe to PATH"** 체크
- Mac: python.org 설치 파일 또는 `brew install python@3.13`

**4. (Windows만) PowerShell 스크립트 실행 허용** — 한 번만, 물어보면 `Y`
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**5. 코드 받기** — 비공개 레포라 GitHub 메일로 온 초대를 먼저 수락하고, 처음엔 GitHub 로그인 창이 뜨면 로그인
```
git clone https://github.com/nokzzeup/receipt-settlement.git
cd receipt-settlement
```

**6. 실행** — 아래 "매일: 실행"과 같음. 처음 한 번은 설치(파이썬 가상환경·패키지·DB·프론트 패키지)를 자동으로 하느라 2~3분 걸린다.

---

## 매일: 실행

### 더블클릭 (제일 쉬움)
| Windows | Mac |
|---|---|
| `start-windows.bat` 더블클릭 | `start-mac.command` 더블클릭 |

- 처음이거나 `git pull`로 패키지가 바뀌었으면 **설치부터 자동으로** 한다
- 서버가 다 뜨면 **브라우저가 자동으로** http://127.0.0.1:5173 을 연다 (localhost:5173도 같음) → 화면 맨 위 **`DEV · 백엔드: API ok · DB ok`** 확인
- 이미 켜져 있을 때 또 더블클릭하면 브라우저만 다시 연다
- 실패하면 창이 `계속하려면 아무 키나 누르십시오`에서 멈춘다 → **그 위의 메시지**를 복사해서 공유
- **끄기: 그 검은 창(터미널)을 닫기**
- Mac에서 처음 더블클릭할 때 "확인되지 않은 개발자" 경고가 뜨면: 파일 우클릭 → 열기

### 터미널에서
```
npm start        # 더블클릭과 같음 (필요하면 설치 → 실행 → 브라우저 열기)
npm run dev      # 실행만 (브라우저는 직접 열기)
```
- 백엔드 API 문서: http://localhost:8000/docs
- 코드를 저장하면 백엔드·프론트 둘 다 자동으로 반영됨
- 끄기: `Ctrl + C`
- 터미널에 `[api]`(백엔드)와 `[web]`(프론트) 로그가 같이 나온다

### Git으로 같이 작업하기
```
git pull                       # 작업 시작 전에 항상 (패키지가 바뀌었으면 다음 실행 때 자동 설치)
git add -A
git commit -m "무엇을 했는지"
git push                       # 거절되면 git pull 후 다시 push
```

---

## 명령 모음 (전부 프로젝트 맨 위 폴더에서)

| 명령 | 하는 일 |
|---|---|
| `npm start` | 필요하면 설치 → 백엔드 + 프론트 실행 → 브라우저 열기 (더블클릭 실행과 같음) |
| `npm run dev` | 백엔드 + 프론트 실행 |
| `npm run dev:host` | 폰에서도 접속 가능하게 실행 (아래 "폰에서 테스트") |
| `npm run serve` | 팀 공용 서버로 실행 (server 파일 더블클릭과 같음, 아래 "팀 공용 서버") |
| `npm test` | 백엔드 테스트 |
| `npm run db:revision "add xxx"` | 모델 수정 후 마이그레이션 생성 → **생성된 파일 꼭 읽어보기** |
| `npm run db:upgrade` | 마이그레이션 적용 (`npm run dev`가 시작할 때 자동으로 함) |
| `npm run db:check` | 모델과 마이그레이션이 어긋났는지 검사 |
| `npm run gen:api` | 프론트 API 타입 갱신 (`npm run dev` 실행 중일 때) |
| `npm run build` / `npm run lint` | 프론트 빌드 / 린트 (PR 전에) |
| `npm run setup` | 설치만 따로 (더블클릭/`npm start`는 필요할 때 알아서 함) |

- **DB 내용 보기**: 무료 프로그램 [DB Browser for SQLite](https://sqlitebrowser.org)로 `backend/data/app.db` 열기
- **DB 초기화**: `npm run dev`를 끄고 `backend/data/` 안의 `app.db*` 파일을 지운 뒤 다시 `npm run dev`

---

## 폰에서 테스트 (카메라 촬영)

1. PC와 폰을 같은 와이파이에 연결
2. `npm run dev:host` → 터미널의 `Network: http://192.168.x.x:5173` 주소를 폰 브라우저로 열기
- Windows는 처음 실행할 때 방화벽 팝업에서 "개인 네트워크" 허용
- 학교 공용 와이파이는 기기끼리 접속이 막혀 있는 경우가 많음 → 핫스팟 사용
- 촬영은 이 상태로 되지만, PWA 설치·오프라인 기능은 HTTPS에서만 동작 → 필요해질 때 따로 준비
- 이건 개발 중 확인용. 여러 명이 **같은 데이터로 같이 쓰는 건** 아래 "팀 공용 서버"

---

## 팀 공용 서버 (노트북 한 대를 서버로)

여러 명이 같은 데이터를 쓰려면 PC 한 대(팀장 노트북)를 서버로 켜고, 다른 사람은 그 주소로 접속한다.
(개발용 실행은 PC마다 데이터가 따로라서 같이 쓰는 용도가 아님)

| Windows | Mac | 터미널 |
|---|---|---|
| `server-windows.bat` 더블클릭 | `server-mac.command` 더블클릭 | `npm run serve` |

1. 창에 뜨는 주소를 확인한다
   ```
   이 노트북:                  http://127.0.0.1:8080
   같은 와이파이의 PC·폰:      http://192.168.0.12:8080   (Wi-Fi)
   다른 와이파이·LTE에서도 접속:  https://단어-단어-단어-단어.trycloudflare.com
   ```
2. 다른 PC·폰의 브라우저에서 주소를 열고 회원가입·로그인해서 쓴다. 폰은 촬영 버튼을 누르면 카메라가 바로 열림
   - 같은 와이파이면 두 번째 주소, **다른 와이파이·LTE면 세 번째(https) 주소** — 세 번째는 어디서나 됨
3. 처음 켤 때 Windows 방화벽 창이 뜨면 **허용** (같은 와이파이 주소에 필요. https 주소는 방화벽과 상관없음)

**다른 와이파이·LTE에서 접속 (https 주소)**
- Cloudflare의 무료 터널(Quick Tunnel)을 쓴다. 서버가 켜질 때 `cloudflared`를 같이 띄워서 주소를 받아옴 — 계정·설치 필요 없음
  (처음 한 번 공식 파일을 내려받아 `.tools/`에 둠. 버전 고정 + 체크섬 확인)
- **서버를 켤 때마다 주소가 바뀐다** → 켤 때마다 팀 단톡방에 새 주소를 공유. 바뀌면 로그인을 다시 해야 함
- https라서 폰에서 "홈 화면에 추가"로 앱처럼 쓸 수 있음 (단, 주소가 바뀌면 다시 추가)
- 주소를 아는 사람은 누구나 로그인 화면까지는 들어올 수 있다. 데이터는 로그인 + 조직 초대 코드로 보호되고, 같은 계정으로 10분에 10번 틀리면 잠시 로그인이 막힘
- 안 만들어지면 창에 이유가 나옴. 같은 와이파이 접속은 그대로 동작. 학교·회사 네트워크가 막는 경우가 있음 → 핫스팟으로 다시 켜기
- 끄려면 `.env`에 `SERVER_TUNNEL=off` (같은 와이파이 전용)
- Cloudflare 안내상 "테스트·개발용, 가동 보장 없음". 실사용 테스트 때 고정 주소가 필요하면 Tailscale Funnel 등으로 바꾼다

- 하는 일: (필요하면 설치) → 화면 빌드 → DB 자동 백업 → DB 구조 업데이트 → 서버 실행. **끄기: 창 닫기**
- **데이터는 `server-data/` 폴더** (DB·영수증 사진·로그인 키). 개발용 `backend/data`와 따로라서 처음엔 회원가입부터. git에 안 올라감
- 개발용 실행(start 파일)과 **동시에 켜도 됨** — 포트(개발 5173·8000 / 서버 8080)와 데이터가 다름
- 코드 업데이트: 서버 창 닫기 → `git pull` → 다시 더블클릭 (화면 빌드·DB 업데이트는 자동)
- 백업: 켤 때마다 DB가 `server-data/backups/`에 자동 저장(최근 10개). 영수증 사진까지 보관하려면 서버를 끄고 `server-data` 폴더째 복사.
  되돌리기: 서버를 끄고 백업 파일을 `server-data/app.db`로 덮어쓴 뒤 다시 켜기
- 포트를 바꾸려면 `.env`의 `SERVER_PORT`

주의
- 노트북이 꺼지거나 절전·덮개 닫힘이면 아무도 못 씀 → 서버로 쓰는 동안은 절전 끄기
- 같은 와이파이 주소(http)는 암호화가 안 됨 → 카페·학교 같은 공용 와이파이에선 https 주소를 쓰는 게 안전
- 학교 와이파이는 기기끼리 막혀 있는 경우가 많음 → https 주소를 쓰거나 노트북 핫스팟에 연결
- 공용 서버에서는 API 문서(`/docs`)를 끈다 (개발 모드에서만 보임)

---

## 폴더 구조

```
.
├── start-windows.bat         더블클릭 실행 — 개발용 (Windows)
├── start-mac.command         더블클릭 실행 — 개발용 (Mac)
├── server-windows.bat        더블클릭 실행 — 팀 공용 서버 (Windows)
├── server-mac.command        더블클릭 실행 — 팀 공용 서버 (Mac)
├── server-data/              공용 서버의 DB·영수증 사진·백업 (git 제외, 서버 PC에만 생김)
├── .tools/                   공용 서버가 내려받는 외부 접속 도구 cloudflared (git 제외)
├── package.json              실행 명령 모음 (npm start / dev / test ...)
├── docs/                     PROJECT.md(범위·규칙·모델), DECISIONS.md(설계 결정과 이유)
├── scripts/                  위 명령이 부르는 실행 스크립트 + 정확도 측정 등 유틸
├── .env.example              환경변수 견본 (setup이 .env로 복사, .env는 커밋 금지)
├── backend/
│   ├── requirements*.txt     파이썬 패키지 (버전 고정)
│   ├── data/                 SQLite DB 파일 (git 제외)
│   ├── storage/              업로드 이미지 (git 제외)
│   ├── app/
│   │   ├── main.py           FastAPI 앱
│   │   ├── web.py            공용 서버 모드에서 빌드된 화면을 같이 내보내기
│   │   ├── ops/              운영 도구 (DB 백업)
│   │   ├── core/             설정(config.py), 시간대(timezone.py)
│   │   ├── api/              라우터 — v1/*.py (auth, orgs, categories, expenses), deps.py(권한)  (이성민)
│   │   ├── schemas/          API 요청·응답 스키마 (바뀌면 프론트 gen:api)          (이성민)
│   │   ├── receipts/         영수증 접수: 이미지 검증·저장, 카드번호 마스킹, OCR 호출  (이성민)
│   │   ├── db/               Base, 세션, 커스텀 타입, migrations/ (Alembic)     (김도현)
│   │   ├── models/           도메인 모델 9개                                      (김도현)
│   │   ├── ocr/              OcrEngine 인터페이스, Mock/Paddle 엔진              (김도현)
│   │   ├── parsing/          ReceiptFields 스키마 + parse() (1차 규칙 기반)         (이성민)
│   │   ├── classify/         품목 → 계정과목 분류 (4단계), 기본 계정과목            (이성민)
│   │   └── settlement/       정산 엔진 (5단계)                                     (이성민)
│   └── tests/
├── frontend/                 React PWA                                              (신율겸)
│   └── src/
│       ├── router.tsx        화면 경로 목록
│       ├── api/              client.ts(타입 있는 fetch), schema.d.ts(자동 생성), 기능별 훅
│       ├── lib/format.ts     금액·한국시간 표시, 정수 입력 변환
│       ├── layouts/  pages/  components/  hooks/
└── dataset/                  테스트 영수증 + 정답 라벨 (형식: dataset/README.md)
```

---

## 팀원별 시작 지점

### 이성민 — 백엔드 API · 파싱 · 분류 · 정산
- `backend/app/api/v1/` — 1·2단계 완료. 조직 안 API는 `api/deps.py`의 `CurrentMembership`(멤버 아니면 404) / `require_roles(...)`(역할 아니면 403)를 반드시 거친다
- `backend/app/parsing/parser.py` — 1차(규칙 기반) 있음. 3단계에서 실제 PaddleOCR 출력을 `tests/test_parser.py`에 케이스로 추가하면서 보강
- `classify/` — 4단계: 업로드 때 품목 자동 분류 자리는 `receipts/intake.py`에 표시해 둠. `settlement/` — 5단계, pytest 필수

### 김도현 — DB · OCR · 데이터셋
- `backend/app/ocr/paddle.py` — 3단계 PaddleOCR 엔진. 설치할 버전을 먼저 정해서 팀에 공유 (버전별 API 차이 큼). `.env`의 `OCR_ENGINE=paddle`로 전환
  - 업로드되면 `recognize(이미지 바이트)`가 불린다. 들어오는 형식은 JPG·PNG·WEBP(15MB 이하)
  - 폰 사진은 EXIF 회전 정보만 있고 실제 픽셀은 누워 있는 경우가 많음 → 디코딩할 때 회전이 적용되는지 설치 버전에서 확인
  - 엔진이 예외를 던져도 업로드는 성공하고 "인식 실패, 직접 입력"으로 처리됨 (로그에 남음)
- `backend/app/models/` — 모델 수정하면 `npm run db:revision "설명"` → 생성 파일 검토 → `npm run db:check`
- `dataset/` — 영수증 수집·라벨링 (형식: `dataset/README.md`)

### 신율겸 — 프론트 PWA
- 동작하는 화면: 로그인, 조직 선택, 조직 설정(초대 코드·역할·계정과목), 지출 목록, 영수증 촬영, 지출 확인·수정(`ExpenseDetailPage` + `components/ExpenseForm.tsx`). 남은 화면: 정산 현황(5단계)
- 디자인은 `frontend/src/index.css` — 색·간격 변수(`:root`) 바꾸면 전체 반영. 화면 구조는 그대로 두고 스타일만 바꿔도 됨
- `frontend/vite.config.ts` — PWA 앱 이름·색, `frontend/public/` 아이콘 교체
- API 호출은 `src/api/client.ts`의 `api.GET/POST(...)` + `unwrap()` + TanStack Query 훅 (`src/api/expenses.ts`가 예시). 로그인 토큰은 자동으로 붙고, 401이면 로그인 화면으로 이동
- 백엔드 API가 바뀌면 `npm run gen:api` (백엔드 켜둔 상태) → `src/api/schema.d.ts` 갱신

---

## 팀 규칙 (요약)

- `OcrRawResult`(`app/ocr/schemas.py`) / `ReceiptFields`(`app/parsing/schemas.py`)는 **합의 없이 변경 금지**
- 금액·수량은 `int`만, 시간은 시간대 있는 값만 저장 → 어기면 DB 저장 단계에서 에러가 나게 해둠 (`app/db/types.py`)
- API는 전부 `/api/v1` 아래, 프론트 타입은 `npm run gen:api`로 생성 (손으로 타입 쓰지 않기)
- `.env` 커밋 금지 — 새 설정값을 추가하면 `.env.example`에도 추가
- 마이그레이션을 두 사람이 동시에 만들면 갈래가 2개가 됨 → 만들기 전에 pull, 생기면 `backend/.venv` 파이썬으로 `alembic merge heads`

---

## PostgreSQL로 바꾸려면 (필요할 때만)

1. `backend/.venv` 파이썬으로 `pip install "psycopg[binary]"`
2. `.env`의 `DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/dbname`
3. `npm run db:upgrade`

같은 마이그레이션·테스트가 PostgreSQL 16에서도 통과하는 것을 확인해뒀다.

---

## 문제 해결

| 증상 | 해결 |
|---|---|
| `npm : 이 시스템에서 스크립트를 실행할 수 없으므로...` | 위 설치 3번 (`Set-ExecutionPolicy ...`) |
| setup에서 `Python 3.13(또는 3.12)이 필요합니다` | 3.13 설치 후 **터미널을 새로 열고** 다시 `npm run setup` |
| setup에서 `Node.js ... 22.22 이상이 필요합니다` | nodejs.org에서 24 LTS 설치 |
| `npm run dev`에서 `먼저 npm run setup 을 실행하세요` | 말 그대로 setup부터 |
| `포트 8000/5173를 이미 다른 프로그램이 쓰고 있어요` | 다른 창에 서버가 켜져 있음 → 그 창을 닫고 다시 실행. 켜둔 창이 없으면 PC 재시작 |
| `Windows가 포트 ...를 예약해둬서 쓸 수 없어요` | Docker·WSL 설치 후 생기는 문제. 관리자 PowerShell에서 `net stop winnat` → `net start winnat` 후 다시 실행 |
| (Windows) 실행 창 안을 클릭했더니 서버가 멈춘 것 같음 | 창이 '선택 모드'로 바뀐 것 → `Esc`를 누르면 다시 진행 |
| 화면 위 표시줄이 `연결 실패` | 터미널의 `[api]` 로그에 에러가 있는지 확인 |
| 다른 PC·폰에서 공용 서버 주소가 안 열림 | ① 같은 와이파이인지 ② 서버 창이 켜져 있는지 ③ Windows 보안 → 방화벽 및 네트워크 보호 → 방화벽에서 앱 허용 → `python.exe`의 '개인' 체크 ④ 설정 → 네트워크 및 인터넷 → Wi-Fi에서 네트워크 프로필을 '개인'으로 ⑤ 학교 와이파이면 노트북 핫스팟으로 |
| 공용 서버 창에 `외부 접속 주소를 만들지 못했어요` | 인터넷 연결 확인. 학교·회사 네트워크가 터널을 막는 경우가 있음 → 핫스팟으로 서버를 다시 켜기. 같은 와이파이 주소는 그대로 됨 |
| https 주소가 `연결할 수 없음`/에러 | 서버 창이 꺼졌거나 다시 켜서 주소가 바뀐 것 → 서버 창에 뜬 최신 주소로 접속 |
| `로그인 실패가 너무 많아요` | 같은 계정으로 10분에 10번 틀려서 잠시 막힌 것 → 메시지의 시간만큼 기다리기 (서버를 다시 켜도 풀림) |
| 공용 서버 화면이 예전 그대로 | 서버 창을 닫고 다시 켜기 (켤 때마다 화면을 새로 빌드함). 그래도 같으면 브라우저 새로고침 |
| `database is locked` | DB Browser for SQLite에서 저장 안 한 변경이 있으면 생김 → 저장하거나 닫기 |
| `git push`가 `rejected`로 거절됨 | 그 사이 팀원이 먼저 올린 것 → `git pull` 후 다시 `git push` |
| git에서 손대지 않은 파일이 통째로 바뀐 것으로 보임 | 줄바꿈(CRLF/LF) 차이. `git add --renormalize .` 한 번 실행 |
