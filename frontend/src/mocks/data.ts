import type { AssistantAnswer } from '../api/assistant'
import type { DocumentReview, DocumentSummary, ParagraphDiff } from '../api/documents'
import type { ConfirmedChange, ReceivedNotification, SentChange } from '../api/notifications'
import type { CompanyUser } from '../api/organizations'
import type {
  PendingApproval,
  Project,
  ProjectMember,
  ProjectMetric,
  ProjectTeam,
} from '../api/project'
import type { AnalysisStep, ImpactCandidate } from '../api/submissions'

// 백엔드 구현 API(회사·프로젝트·팀)와 같은 모양의 목업. 테스트 계정 비밀번호는 목업 전용
export const accounts: (CompanyUser & { password: string })[] = [
  {
    user_id: 1,
    dept_id: 1,
    name: '홍길동',
    email: 'gildong.hong@hedy.co.kr',
    user_type: 'LIMITED',
    password: 'brain2026!',
  },
  {
    user_id: 2,
    dept_id: 3,
    name: '김민준',
    email: 'minjun.kim@hedy.co.kr',
    user_type: 'MANAGER',
    password: 'brain2026!',
  },
  {
    user_id: 3,
    dept_id: 2,
    name: '박서연',
    email: 'seoyeon.park@hedy.co.kr',
    user_type: 'LIMITED',
    password: 'brain2026!',
  },
]

export const projects: Omit<Project, 'my_role'>[] = [
  { project_id: 1, name: '쇼핑몰 구축', status: 'START', created_at: '2026-09-01T09:00:00' },
  { project_id: 2, name: '회원 리뉴얼', status: 'START', created_at: '2026-11-01T09:00:00' },
  { project_id: 3, name: '배송 자동화 PoC', status: 'END', created_at: '2026-06-15T09:00:00' },
]

const SHOP_TEAMS = [
  '기획팀',
  '디자인&퍼블리싱',
  '주문·결제 개발',
  '회원·상품 개발',
  '공통기술·데이터',
  'QA',
  'PMO',
]

export const projectTeams: ProjectTeam[] = SHOP_TEAMS.map((name, i) => ({
  project_team_id: i + 1,
  project_id: 1,
  name,
  team_leader: null,
  team_leader_name: null,
  member_count: 0,
}))

export const projectMembers: (Omit<ProjectMember, 'name' | 'email'> & { project_id: number })[] = [
  {
    project_member_id: 1,
    project_id: 1,
    project_team_id: 1,
    user_id: 1,
    role: 'MEMBER',
    is_approval: 'N',
  },
  {
    project_member_id: 2,
    project_id: 1,
    project_team_id: 7,
    user_id: 2,
    role: 'LEADER',
    is_approval: 'Y',
  },
  {
    project_member_id: 3,
    project_id: 1,
    project_team_id: 3,
    user_id: 3,
    role: 'MEMBER',
    is_approval: 'N',
  },
  {
    project_member_id: 4,
    project_id: 2,
    project_team_id: 1,
    user_id: 1,
    role: 'MEMBER',
    is_approval: 'N',
  },
]

export const metrics: ProjectMetric[] = [
  {
    key: 'headDocuments',
    label: '승인된 HEAD 문서',
    value: '5',
    unit: '건',
    hint: '이번 주 4건 반영',
  },
  { key: 'pendingApprovals', label: '승인 대기', value: '2', unit: '건', hint: '평균 검토 0.8일' },
  { key: 'unreadAlerts', label: '미확인 변경 알림', value: '3', unit: '팀', hint: '2일 경과 1건' },
  { key: 'confirmRate', label: '팀 확인률', value: '25', unit: '%', hint: '4팀 중 1팀 확인' },
]

export const documents: DocumentSummary[] = [
  {
    id: 'req-def',
    name: '요구사항정의서',
    team: '기획팀',
    owner: '홍길동',
    version: 2,
    scope: '프로젝트 내부',
    updatedAt: '11.24 09:10',
    changes: 3,
    pending: false,
    summary: '무료배송 기준 금액과 안내 문구, 적용 시점을 정리했습니다.',
    ext: 'DOCX',
    size: '1.2 MB',
  },
  {
    id: 'ui-guide',
    name: 'UI 가이드',
    team: '디자인&퍼블리싱',
    owner: '홍길동',
    version: 4,
    scope: '사내 공개',
    updatedAt: '11.23 16:40',
    changes: 2,
    pending: false,
    summary: '장바구니 무료배송 배지 위치를 결제 버튼 위로 이동했습니다.',
    ext: 'PPTX',
    size: '9.6 MB',
  },
  {
    id: 'shipping-api',
    name: '배송비 계산 API 명세서',
    team: '주문·결제 개발',
    owner: '홍길동',
    version: 2,
    scope: '프로젝트 내부',
    updatedAt: '11.22 14:05',
    changes: 1,
    pending: false,
    summary: '도서산간 추가 배송비가 5,000원으로 조정되었습니다.',
    ext: 'MD',
    size: '92 KB',
  },
  {
    id: 'order-table',
    name: '주문 테이블 정의서',
    team: '공통기술·데이터',
    owner: '홍길동',
    version: 1,
    scope: '팀 내부',
    updatedAt: '11.20 11:12',
    changes: 1,
    pending: true,
    summary: '주문·배송 테이블 컬럼과 무료배송 여부 플래그를 정의합니다.',
    ext: 'XLSX',
    size: '486 KB',
  },
  {
    id: 'qa-case',
    name: 'QA 테스트 케이스',
    team: 'QA',
    owner: '홍길동',
    version: 5,
    scope: '외부 공유',
    updatedAt: '11.24 08:55',
    changes: 4,
    pending: false,
    summary: '무료배송 경계값 케이스 4건이 추가되었습니다.',
    ext: 'XLSX',
    size: '1.1 MB',
  },
]

const reqDefSummary = [
  '무료배송 기준이 5만 원에서 7만 원으로 올랐습니다.',
  "상품·장바구니의 무료배송 안내 문구가 '7만 원 이상'으로 바뀝니다.",
  '12월 1일 주문부터 적용됩니다.',
]

export const confirmedChanges: ConfirmedChange[] = [
  {
    id: 'chg-1',
    docId: 'req-def',
    doc: '요구사항정의서',
    from: 'v1',
    to: 'v2',
    time: '오늘 09:10',
    unread: true,
    summary: reqDefSummary,
    teams: [
      { name: 'QA', state: 'done', by: '홍길동' },
      { name: '디자인&퍼블리싱', state: 'pending', by: '' },
      { name: '주문·결제 개발', state: 'pending', by: '' },
      { name: '공통기술·데이터', state: 'pending', by: '' },
    ],
  },
  {
    id: 'chg-2',
    docId: 'ui-guide',
    doc: 'UI 가이드',
    from: 'v3',
    to: 'v4',
    time: '어제 16:40',
    unread: false,
    summary: [
      '장바구니 무료배송 배지 위치가 결제 버튼 위로 이동했습니다.',
      "배지 문구가 '7만 원 이상 무료배송'으로 갱신되었습니다.",
      '모바일 장바구니에서도 같은 위치를 사용합니다.',
    ],
    teams: [
      { name: '디자인&퍼블리싱', state: 'done', by: '홍길동' },
      { name: '주문·결제 개발', state: 'done', by: '홍길동' },
    ],
  },
  {
    id: 'chg-3',
    docId: 'shipping-api',
    doc: '배송비 계산 API 명세서',
    from: 'v1',
    to: 'v2',
    time: '11.22 14:05',
    unread: false,
    summary: [
      '도서산간 추가 배송비가 3,000원에서 5,000원으로 바뀌었습니다.',
      '무료배송 기준 금액이 70,000원으로 조정되었습니다.',
      '제주·도서산간 판정 기준이 우편번호 단위로 명시되었습니다.',
    ],
    teams: [
      { name: '주문·결제 개발', state: 'done', by: '홍길동' },
      { name: '공통기술·데이터', state: 'done', by: '홍길동' },
    ],
  },
  {
    id: 'chg-4',
    docId: 'qa-case',
    doc: 'QA 테스트 케이스',
    from: 'v4',
    to: 'v5',
    time: '11.24 08:55',
    unread: true,
    summary: [
      '무료배송 경계값 케이스 4건이 추가되었습니다.',
      '69,999원과 70,000원 주문의 배송비 계산을 검증합니다.',
      '12월 1일 이전 주문의 기존 기준 회귀 케이스도 포함했습니다.',
    ],
    teams: [
      { name: 'QA', state: 'done', by: '홍길동' },
      { name: '주문·결제 개발', state: 'pending', by: '' },
    ],
  },
]

export const pendingApprovals: PendingApproval[] = [
  {
    id: 'ap-1',
    docId: 'ui-guide',
    doc: 'UI 가이드',
    version: 'v5',
    submitter: '홍길동',
    team: '디자인&퍼블리싱',
    time: '2시간 전',
  },
  {
    id: 'ap-2',
    docId: 'order-table',
    doc: '주문 테이블 정의서',
    version: 'v2',
    submitter: '홍길동',
    team: '공통기술·데이터',
    time: '어제 20:15',
  },
]

function unchanged(id: string, index: number, text: string): ParagraphDiff {
  return {
    id,
    type: 'unchanged',
    before: text,
    after: text,
    author: null,
    version: null,
    location: { index },
  }
}

export const reviewParagraphs: ParagraphDiff[] = [
  unchanged('p1', 1, '4. 주문·배송 정책'),
  unchanged('p2', 2, 'FR-011 주문 취소 — 결제 완료 후 24시간 이내에는 고객이 직접 취소할 수 있다.'),
  {
    id: 'p3',
    type: 'modified',
    before: 'FR-012 무료배송 기준 금액: 50,000원 이상',
    after: 'FR-012 무료배송 기준 금액: 70,000원 이상',
    author: '홍길동',
    version: 'v2',
    location: { index: 3 },
  },
  {
    id: 'p4',
    type: 'modified',
    before: '상품 상세·장바구니 안내 문구 — “5만 원 이상 무료배송”',
    after: '상품 상세·장바구니 안내 문구 — “7만 원 이상 무료배송”',
    author: '홍길동',
    version: 'v2',
    location: { index: 4 },
  },
  {
    id: 'p5',
    type: 'added',
    before: null,
    after:
      '변경된 기준은 12월 1일 주문부터 적용한다. 11월 30일 이전에 생성된 주문에는 기존 5만 원 기준이 유지된다.',
    author: '홍길동',
    version: 'v2',
    location: { index: 5 },
  },
  unchanged(
    'p6',
    6,
    'FR-013 도서산간 배송비 — 제주 및 도서산간 지역은 추가 배송비 5,000원을 부과한다.',
  ),
  unchanged(
    'p7',
    7,
    'FR-014 배송비 표시 — 결제 화면에서 상품 금액, 배송비, 최종 결제 금액을 분리해 표시한다.',
  ),
  unchanged(
    'p8',
    8,
    'FR-015 반품 배송비 — 단순 변심 반품 시 왕복 배송비 6,000원을 고객이 부담한다. (11.21 다른 제출자 반영분)',
  ),
]

export const documentReview: DocumentReview = {
  id: 'req-def',
  name: '요구사항정의서',
  team: '기획팀',
  owner: '홍길동',
  submitter: '홍길동',
  fileName: '요구사항정의서_v2.docx',
  headVersion: 'v1',
  candidateVersion: 'v2',
  baseVersion: 'HEAD v1',
  submittedAt: '2026.11.24 09:10',
  scope: '프로젝트 내부',
  ext: 'DOCX',
  size: '1.2 MB',
  lines: 128,
  summary: reqDefSummary,
  verification: { passed: true, rewrites: 1, checkedAt: '09:10', agent: '요약·검증 에이전트' },
  overwrite: {
    count: 1,
    message:
      'HEAD 덮어쓰기 1곳 감지: 다른 사람이 먼저 고친 FR-015 반품 배송비 문단이 이 파일에 없습니다. 그대로 반영하면 그 변경이 사라집니다.',
  },
  parser: { engine: 'Docling', paragraphCount: 8 },
  paragraphs: reviewParagraphs,
  changeItems: [
    { paragraphId: 'p3', type: '수정', label: 'FR-012 무료배송 기준 50,000원 → 70,000원' },
    { paragraphId: 'p4', type: '수정', label: "안내 문구 '7만 원 이상 무료배송'으로 변경" },
    { paragraphId: 'p5', type: '추가', label: '12월 1일 주문부터 적용 명시' },
  ],
  teams: [
    {
      name: '디자인&퍼블리싱',
      reason: 'UI 가이드의 무료배송 배지 문구',
      confidence: '높음',
      state: 'pending',
      by: '',
      response: null,
    },
    {
      name: '주문·결제 개발',
      reason: '배송비 계산 API의 기준 금액',
      confidence: '높음',
      state: 'pending',
      by: '',
      response: null,
    },
    {
      name: '공통기술·데이터',
      reason: '주문 테이블의 무료배송 여부 컬럼',
      confidence: '보통',
      state: 'pending',
      by: '',
      response: null,
    },
    {
      name: 'QA',
      reason: '경계값(69,999원/70,000원) 테스트 케이스',
      confidence: '높음',
      state: 'done',
      by: '홍길동',
      response: '확인 완료',
    },
  ],
}

export const receivedNotifications: ReceivedNotification[] = [
  {
    id: 'ntf-1',
    docId: 'req-def',
    doc: '요구사항정의서',
    version: 'v2',
    time: '2시간 전',
    from: '홍길동 · 기획팀',
    unread: true,
    overdue: false,
    summary: reqDefSummary,
    targetTeams: ['주문·결제 개발'],
  },
  {
    id: 'ntf-2',
    docId: 'ui-guide',
    doc: 'UI 가이드',
    version: 'v4',
    time: '어제 16:40',
    from: '홍길동 · 디자인&퍼블리싱',
    unread: true,
    overdue: false,
    summary: [
      '장바구니 무료배송 배지 위치가 결제 버튼 위로 이동했습니다.',
      "배지 문구가 '7만 원 이상 무료배송'으로 갱신되었습니다.",
      '모바일 장바구니에도 같은 위치를 적용합니다.',
    ],
    targetTeams: ['주문·결제 개발'],
  },
  {
    id: 'ntf-3',
    docId: 'shipping-api',
    doc: '배송비 계산 API 명세서',
    version: 'v2',
    time: '2일 전',
    from: '홍길동 · 주문·결제 개발',
    unread: true,
    overdue: true,
    summary: [
      '도서산간 추가 배송비가 3,000원에서 5,000원으로 바뀌었습니다.',
      '무료배송 기준 금액이 70,000원으로 조정되었습니다.',
      '제주·도서산간 판정 기준이 우편번호 단위로 명시되었습니다.',
    ],
    targetTeams: ['주문·결제 개발'],
  },
  {
    id: 'ntf-4',
    docId: 'qa-case',
    doc: 'QA 테스트 케이스',
    version: 'v5',
    time: '3일 전',
    from: '홍길동 · QA',
    unread: false,
    overdue: false,
    summary: [
      '무료배송 경계값 케이스 4건이 추가되었습니다.',
      '69,999원과 70,000원 주문의 배송비 계산을 검증합니다.',
      '12월 1일 이전 주문의 회귀 케이스도 포함했습니다.',
    ],
    targetTeams: ['주문·결제 개발'],
  },
]

export const sentChanges: SentChange[] = [
  {
    id: 'sent-1',
    docId: 'req-def',
    doc: '요구사항정의서',
    version: 'v2',
    time: '오늘 09:10',
    status: '확인 진행',
    summary: reqDefSummary,
    targetTeams: [
      { name: 'QA', state: 'done', by: '홍길동' },
      { name: '디자인&퍼블리싱', state: 'pending', by: '' },
      { name: '주문·결제 개발', state: 'pending', by: '', note: '2일 경과 · 리마인드 발송됨' },
      { name: '공통기술·데이터', state: 'pending', by: '' },
    ],
  },
  {
    id: 'sent-2',
    docId: 'ui-guide',
    doc: 'UI 가이드',
    version: 'v4',
    time: '어제 16:40',
    status: '확인 완료',
    summary: [
      '장바구니 무료배송 배지 위치가 결제 버튼 위로 이동했습니다.',
      "배지 문구가 '7만 원 이상 무료배송'으로 갱신되었습니다.",
      '모바일 장바구니에도 같은 위치를 적용합니다.',
    ],
    targetTeams: [
      { name: '디자인&퍼블리싱', state: 'done', by: '홍길동' },
      { name: '주문·결제 개발', state: 'done', by: '홍길동' },
    ],
  },
  {
    id: 'sent-3',
    docId: 'shipping-api',
    doc: '배송비 계산 API 명세서',
    version: 'v2',
    time: '11.22 14:05',
    status: '확인 완료',
    summary: [
      '도서산간 추가 배송비가 3,000원에서 5,000원으로 바뀌었습니다.',
      '무료배송 기준 금액이 70,000원으로 조정되었습니다.',
      '제주·도서산간 판정 기준이 우편번호 단위로 명시되었습니다.',
    ],
    targetTeams: [
      { name: '주문·결제 개발', state: 'done', by: '홍길동' },
      { name: '공통기술·데이터', state: 'done', by: '홍길동' },
    ],
  },
]

export const analysisSteps: AnalysisStep[] = [
  { label: '파일 검증 · 악성 파일 검사', detail: 'DOCX · 1.2MB · 허용 확장자' },
  { label: '문단 추출 (Docling)', detail: '문단 12개 · 표 2개' },
  { label: 'HEAD 차이 검사', detail: 'HEAD v1 대비 바뀐 문단 3곳' },
  { label: 'LLM 영향 팀 판정', detail: '프로젝트 7개 팀 일괄 판정' },
  { label: '3줄 요약 · 검증 에이전트', detail: '재작성 1회 후 검증 통과' },
]

export const impactCandidates: ImpactCandidate[] = [
  {
    name: '디자인&퍼블리싱',
    checked: true,
    confidence: '높음',
    reason: 'UI 가이드의 무료배송 배지 문구',
  },
  {
    name: '주문·결제 개발',
    checked: true,
    confidence: '높음',
    reason: '배송비 계산 API의 기준 금액',
  },
  {
    name: '공통기술·데이터',
    checked: true,
    confidence: '보통',
    reason: '주문 테이블의 무료배송 여부 컬럼',
  },
  {
    name: 'QA',
    checked: true,
    confidence: '높음',
    reason: '경계값(69,999원/70,000원) 테스트 케이스',
  },
  { name: '회원·상품 개발', checked: false, confidence: '낮음', reason: '상품·회원 데이터와 무관' },
  { name: 'PMO', checked: false, confidence: '낮음', reason: '일정·범위 변동 없음' },
]

export const assistantKnowledge: { keywords: string[]; answer: AssistantAnswer }[] = [
  {
    keywords: ['무료배송', '배송 기준', '배송비', '무료 배송'],
    answer: {
      text: '7만 원입니다. 12월 1일 주문부터 적용됩니다.',
      sources: [{ doc: '요구사항정의서', version: 'HEAD v2', section: 'FR-012' }],
    },
  },
  {
    keywords: ['지난주', '이번주', '뭐 바뀐', '변경 이력'],
    answer: {
      text: '지난주에는 4개 문서가 승인되었습니다. ① 요구사항정의서 v1→v2: 무료배송 기준 5만 원 → 7만 원, ② UI 가이드 v3→v4: 장바구니 무료배송 배지 위치를 결제 버튼 위로 이동, ③ 배송비 계산 API 명세서 v1→v2: 도서산간 추가 배송비 3,000원 → 5,000원, ④ QA 테스트 케이스 v4→v5: 무료배송 경계값 4건 추가.',
      sources: [
        { doc: '요구사항정의서', version: 'HEAD v2', section: '4. 주문·배송 정책' },
        { doc: '배송비 계산 API 명세서', version: 'HEAD v2', section: '2. 배송비 계산' },
      ],
    },
  },
  {
    keywords: ['영향', '우리 팀'],
    answer: {
      text: '이번 요구사항정의서 v2는 QA팀에 직접 영향이 있습니다. 69,999원과 70,000원 경계값 케이스를 다시 확인해야 하고, 12월 1일 이전 주문의 기존 기준 회귀 테스트도 필요합니다. 알림 대상에는 디자인&퍼블리싱, 주문·결제 개발, 공통기술·데이터, QA 4팀이 포함되었습니다.',
      sources: [
        { doc: '요구사항정의서', version: '검토 중 v2', section: 'FR-012 · 적용 시점' },
        { doc: 'QA 테스트 케이스', version: 'HEAD v5', section: '무료배송 경계값 4건' },
      ],
    },
  },
  {
    keywords: ['확인', '할 일', '미확인'],
    answer: {
      text: '확인하지 않은 변경 알림이 3건 있습니다. 그중 배송비 계산 API 명세서 v2는 2일이 지나 리마인드가 발송된 상태입니다. 요구사항정의서 v2는 4팀 중 QA만 확인을 마쳤습니다.',
      sources: [
        {
          doc: '변경 알림',
          version: '미확인 3건',
          section: '리마인드 1건 · 요구사항정의서 v2 1/4',
        },
      ],
    },
  },
  {
    keywords: ['최신본', '화면설계서', '장바구니', '최신'],
    answer: {
      text: '장바구니 화면설계서의 최신 기준 문서는 UI 가이드 HEAD v4입니다. 승인 2026.11.23 16:40, 공개 범위는 사내 공개이며, 무료배송 배지는 결제 버튼 위에 배치됩니다. 승인 대기 중인 v5 초안은 검색 대상이 아닙니다.',
      sources: [{ doc: 'UI 가이드', version: 'HEAD v4', section: '장바구니 · 무료배송 배지' }],
    },
  },
]

export const assistantFallback: AssistantAnswer = {
  text: '기준 문서(HEAD)에서 근거를 찾지 못했습니다. 승인된 문서에 없는 내용은 답하지 않습니다. 질문을 문서명이나 요구사항 ID와 함께 다시 적어주세요.',
  sources: [],
}
