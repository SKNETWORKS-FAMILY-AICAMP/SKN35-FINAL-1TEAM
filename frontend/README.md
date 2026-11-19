# 회사 공용 브레인 — 프론트엔드

팀원 웹 화면입니다. 백엔드 API가 준비되기 전까지는 MSW 목업 응답으로 화면을 개발합니다.
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
│  ├─ api/          # 백엔드 호출 함수 + 타입
│  ├─ mocks/        # MSW 핸들러·가짜 데이터
│  ├─ pages/        # 화면 단위
│  ├─ components/   # 여러 화면에서 쓰는 UI 조각
│  ├─ hooks/        # 커스텀 훅 (TanStack Query 훅 등)
│  ├─ App.tsx
│  └─ main.tsx
├─ eslint.config.js
├─ .prettierrc.json
└─ vite.config.ts
```

- `api/`의 타입은 백엔드 계약을 기준으로 맞춥니다. 특히 변경 보기 화면은 `backend/app/pipeline/contracts.py`의 `ParagraphDiff`, `Location`을 따릅니다.
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
- [ ] 라우팅 + 공통 레이아웃 (사이드바, 상단바, 알림 빨간 점)
- [ ] MSW 연결 + 프로젝트 목록·문서 목록 화면
- [ ] 나머지 MVP 화면
