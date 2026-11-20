# CLAUDE.md

- 사용자가 첨부한 파일은 전체 확인한다. 확인하지 못했으면 작업을 중단하고 확인하지 못했음을 명시한다.

# 회사 공용 브레인 (SKN35 최종 프로젝트 1팀)

## 프로젝트 소개
팀 산출물(기획서·화면설계서·인터페이스정의서 등)의 **최종본(HEAD)을 관리하고, 문서가 바뀌면 영향받는 팀에게만 변경 내용을 알려주는 서비스**.
해결하려는 문제는 하나: **변경 전파 누락** (문서가 바뀌었는데 관련 팀이 몰라서 생기는 재작업).

핵심 흐름: 제출 → 텍스트 추출·HEAD와 비교 → LLM이 영향 팀 후보 제안 → 제출자 확정 → 승인자 승인(본인 승인 금지) → HEAD 새 버전 반영 → 확정 팀에 알림(3줄 요약) → 팀원 확인 응답 → 미확인 시 2일마다 리마인드.
부가 기능: HEAD 문서 기반 챗봇(RAG, 출처 필수), MCP 서버(Claude·Cursor·Codex에서 HEAD 검색).

### 용어
| 용어 | 뜻 |
|---|---|
| HEAD | 승인을 거친 문서의 최종본. 버전 v1, v2… |
| 제출본 | 승인 전 문서. "vN 검토 중" 표시, 챗봇·MCP 검색에서 제외 |
| 기준 버전 | 제출자가 받아서 고친 HEAD 버전 (덮어쓰기 검사에 사용) |
| 영향 팀 | 변경 때문에 산출물·코드를 고쳐야 하는 팀 |

상세 문서: `docs/` (기획서, 기능명세서, 아키텍처, 폴더 구조). 기능은 기능명세서의 ID(SUB-01, APV-04 …)로 부른다.

## 아키텍처 요약
**원칙: 흐름은 백엔드(FastAPI)가 지휘하고, Celery 워커와 LangGraph는 실행만 한다.**
- 문서 상태 전이(분석 중 → 승인 대기 → 승인 → 반영 → 알림 완료)는 FastAPI 서비스 계층만 바꾼다
- Celery 작업은 실행 후 결과를 DB에 기록할 뿐, 다음 단계를 결정하지 않는다
- 권한 판정은 LLM이 아니라 DB 규칙으로만 한다

| 레이어 | 구성 |
|---|---|
| Client | 팀원 웹(React), 게스트 웹, MCP 클라이언트 |
| Access | 인증, RBAC(역할 × 공개 범위 4단계), 입력 가드레일, MCP 서버 |
| Application | FastAPI 모듈: documents, analysis, approvals, notifications, chat |
| 실행 | Celery 워커(추출·비교·판정·임베딩), LangGraph(챗봇), Intelligence(bge-m3·LLM), Safety(PII·권한 필터·출처 검증) |
| Data | PostgreSQL + pgvector (그래프 DB 없음), S3(원본), Redis(Celery 큐) |
| Ops | Langfuse, 감사·추론 로그, 어드민, Celery Beat |

### 의존 방향 (역방향 import 금지)
modules / common  →  intelligence · safety · integrations · pipeline  →  core

- `pipeline/`은 순수 Python: fastapi·sqlalchemy·app.modules import 금지
- `modules/`끼리 직접 import 금지. 꼭 필요하면 상대 모듈의 `service.py`만
- 외부 시스템(S3, LLM, 판정 모델)은 `base.py`(Port) + 구현체로 분리


## 폴더 구조
### 단, 폴더 구조는 추후 변경될 수 있음

├─ backend/
│  ├─ app/
│  │  ├─ core/          # 설정, DB 세션, 보안, 로깅
│  │  ├─ common/        # auth, orgs, permissions, audit
│  │  ├─ modules/       # documents, analysis, approvals, notifications, chat, admin
│  │  ├─ pipeline/      # 문서 파싱·엔티티·diff (순수 함수)
│  │  ├─ intelligence/  # judge/(Port+구현), embedding, summarize, prompts/
│  │  ├─ safety/        # 파일 검증, 인젝션, PII 마스킹, 출처 검증
│  │  ├─ integrations/  # storage/, llm/, langfuse
│  │  ├─ worker/        # Celery 앱, tasks/, beat
│  │  └─ mcp_server/    # FastAPI에 마운트, service 재사용
│  ├─ alembic/
│  └─ tests/            # fixtures/, unit/, integration/
├─ frontend/            # Vite + React + TS (frontend/CLAUDE.md 참고)
├─ evaluation/          # datasets/{testset,trainset}/, labeling/, experiments/
└─ docs/                # 기획·설계 문서, adr/, erd/

모듈 내부: `router.py`(HTTP만) / `service.py`(유스케이스·트랜잭션) / `rules.py`(순수 규칙, 필요할 때만) / `models.py` / `schemas.py`.
`utils/`·`shared/` 폴더는 만들지 않는다.

## 브랜치·커밋 규칙
- 브랜치: 개인 이름 브랜치(작업본) → `dev`(통합) → `main`(발표·배포). 기능별 브랜치는 만들지 않음
- 작업은 항상 본인 이름 브랜치에서. `main`, `dev`에 직접 push 금지, PR로 `dev`에 병합
- 이슈는 `.github/ISSUE_TEMPLATE` 사용, PR 본문에 이슈 번호와 기능 ID 적기
- 커밋 메시지: `<타입>: <내용>`
  | 타입 | 쓰는 경우 |
  |---|---|
  | feat | 기능 구현·변경 |
  | fix | 버그 수정 |
  | docs | 문서(README, CLAUDE.md, docs/) 수정 |
  | add | 파일·리소스 추가 (설정 파일, 의존성, 데모 문서, 폴더 구조) |
  - 예: `feat: DOCX 문단 분할 추가 (CHG-01)`, `add: .gitignore 추가`
- `.env`, 대용량 파일(모델 가중치, 대형 테스트 문서) 커밋 금지



## macOS / Windows 혼용 주의사항
- **인코딩**: 파일 입출력은 항상 `encoding="utf-8"` 명시 (Windows 기본값 cp949 → 한글 깨짐)
- **경로**: 문자열 결합 대신 `pathlib.Path` 사용, 경로를 하드코딩하지 않기
- **줄바꿈**: 저장소 `.gitattributes`에 `* text=auto eol=lf` 유지
- **파일명 대소문자**: macOS·Windows는 구분 안 함, 배포 서버(Linux)는 구분함 → import 경로와 파일명 대소문자 정확히 일치
- **Celery**: Windows에서 워커 실행 시 `--pool=solo` 필요. 로컬 개발은 `CELERY_TASK_ALWAYS_EAGER=true`로 Redis 없이 실행
- **DB**: 도커 미사용. 각자 Supabase 무료 프로젝트(PostgreSQL + pgvector)를 만들어 `.env`의 `DATABASE_URL`에 설정
- **패키지·실행**: `uv`로 통일 (`uv sync`, `uv run …`). 가상환경 활성화 명령이 OS마다 다르므로 `uv run`을 우선 사용
- 터미널 명령을 안내할 때는 macOS(zsh)와 Windows(PowerShell)를 함께 적기

## Claude에게
- 기능 구현 시 해당 기능 ID와 기능명세서의 "제약·예외"를 먼저 확인
- 새 폴더·계층·추상화를 추가하기 전에 먼저 제안하고 확인받기
- 다른 파트 폴더(담당자가 다른 곳)는 수정하지 말고, 필요한 변경은 따로 정리해서 알리기