# 회사 공용 브레인 — 프론트엔드

팀원 웹 화면입니다. 백엔드에 구현된 API는 실제로 호출하고, 아직 없는 API는 MSW 목업 응답으로 개발합니다.
프로젝트 전체 소개는 [루트 README](../README.md)를 참고하세요.

## 기술 스택

| 영역 | 기술 |
|---|---|
| 런타임 | Node.js 24 LTS (`.nvmrc`, `package.json`의 `engines`로 고정) |
| 빌드 | Vite |
| UI | React, TypeScript 6.0 |
| 라우팅 | React Router |
| 서버 상태 | TanStack Query |
| 스타일 | Tailwind CSS v4 (`@tailwindcss/vite` 플러그인) |
| API 목업 | MSW |
| 코드 품질 | ESLint, Prettier |

> TypeScript는 7이 아니라 **6.0**을 씁니다. typescript-eslint가 아직 TS 6.0까지만 지원하기 때문입니다.

## 실행 방법

### 1. Node 24 맞추기 (처음 한 번)

```bash
# macOS (zsh) — nvm 또는 fnm
cd frontend
nvm use            # .nvmrc를 읽어 Node 24로 전환 (fnm이면: fnm use)
node -v            # v24.x 확인
```

```powershell
# Windows (PowerShell) — nvm-windows는 .nvmrc를 읽지 않음
cd frontend
nvm use 24
node -v
```

### 2. 설치·실행

```bash
npm install        # 처음 한 번, 또는 package.json이 바뀌었을 때
npm run dev        # http://localhost:5173
```

종료는 터미널에서 `Ctrl+C`.

### 3. API 목업 모드

`.env.example`을 `.env`로 복사한 뒤 `VITE_API_MOCKING`을 고릅니다. (`.env`가 없으면 `all`)

| 값 | 동작 |
|---|---|
| `all` | 전부 목업. 백엔드 없이 개발할 때 |
| `partial` | 구현된 API는 실제 백엔드, 나머지만 목업 |
| `off` | 목업 끔 |

개발 서버는 `/api` 요청을 `VITE_API_PROXY_TARGET`(기본 `http://localhost:8000`)으로 넘깁니다.
`all` 모드에서는 로그인 화면에 테스트 계정이 표시됩니다. (비밀번호 `brain2026!`)

| 계정 | 팀 | 권한 |
|---|---|---|
| gildong.hong@hedy.co.kr | 기획팀 | 팀원 |
| minjun.kim@hedy.co.kr | PMO | 팀장 · 승인권자 |
| seoyeon.park@hedy.co.kr | 주문·결제 개발 | 팀원 |

## 스크립트

| 명령 | 하는 일 |
|---|---|
| `npm run dev` | 개발 서버 실행 (코드 수정 시 화면 즉시 반영) |
| `npm run build` | 타입 검사(`tsc -b`) + 배포용 빌드 → `dist/` |
| `npm run preview` | 빌드 결과 미리보기 |
| `npm run lint` | ESLint 검사 |
| `npm run format` | Prettier로 코드 정리 (`*.md`는 제외) |
| `npm run format:check` | 정리 필요 여부만 검사 |

PR 올리기 전에 `npm run lint`와 `npm run build`가 통과하는지 확인해 주세요.

## 폴더 구조

```
frontend/
├─ public/
│  └─ mockServiceWorker.js   # MSW가 생성한 파일 (직접 수정 금지)
├─ src/
│  ├─ api/          # 백엔드 호출 함수 + 타입 (백엔드 schemas.py 기준)
│  ├─ mocks/        # MSW 핸들러·가짜 데이터 (구현된 API / 미구현 API 분리)
│  ├─ pages/        # 화면 단위. 화면이 크면 폴더로 나눔 (landing/, submit/, document-review/)
│  ├─ components/   # 여러 화면에서 쓰는 UI (layout/ = 사이드바·상단바)
│  ├─ hooks/        # useAuth(로그인 사용자·권한), useToast
│  ├─ assets/       # 이미지
│  ├─ App.tsx       # 라우팅
│  └─ main.tsx
├─ .env.example
└─ vite.config.ts
```

- 권한은 로그인 사용자의 프로젝트 멤버 정보로 판단합니다. 승인은 `is_approval = Y`, 확인 응답은 내 팀이 영향 팀일 때. 제출은 누구나(새 버전은 내 팀 문서만).
- `utils/`·`shared/` 폴더는 만들지 않습니다 (루트 CLAUDE.md 규칙).

## MVP 화면

| # | 화면 | 기능 ID |
|---|---|---|
| 1 | 로그인 | AUTH-01 |
| 2 | 프로젝트 목록 | PRJ-02 |
| 3 | 문서 목록·상세 | SUB-06, NTF-05 |
| 4 | 문서 제출 | SUB-01 |
| 5 | 영향 팀 확인 | IMP-03 |
| 6 | 승인 대기 목록·승인 | APV-03·04·06 |
| 7 | 변경 보기 | CHG-06, NTF-03 |
| 8 | 내 알림 목록 | NTF-06 |
| 9 | 팀별 확인 현황 | NTF-04 |

챗봇(CHAT)과 게스트 화면(AUTH-06·07)은 2단계입니다. 화면별 규칙은 [frontend/CLAUDE.md](CLAUDE.md)에 있습니다.

## 진행 상황

- [x] 프로젝트 생성, 패키지 설치, 폴더 구조
- [x] 라우팅 + 공통 레이아웃 (사이드바, 상단바, 알림 빨간 점)
- [x] 로그인·프로젝트·팀·파일 업로드 백엔드 API 연결
- [x] MVP 화면 (문서 내용·알림·승인·분석은 목업)
- [ ] 백엔드 API 추가되는 대로 목업 교체
