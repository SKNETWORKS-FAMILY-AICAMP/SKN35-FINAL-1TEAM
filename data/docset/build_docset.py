"""DATA-01 가상 SI 문서 세트 생성기 (데이터셋 개정 26.11.19).

데이터셋 개정판은 날짜로 부른다(폴더명 예: 26.11.19쇼핑몰A). v1·v2·v3는 문서 버전에만 쓴다.

  company.py       가상 SI사 인원 풀 (프로젝트 밖에서 관리 → B 프로젝트가 같은 사람 재사용)
  project_a.py     A 프로젝트(가나유통 온라인몰 차세대 구축) 데이터·변경 요청·정답
  project_b.py     B 프로젝트(다온정밀 구매·발주 시스템/협력사 포털) — 7개 확장자, 대리 승인자, 다수 버전
  questions.py     사용자 질문 의도 평가셋 (프로젝트 열 포함)
  build_docset.py  렌더러 + 버전 엔진 + 정답 생성 + 교차 검증 (이 파일)

파일 형식: 모델 종류(xlsx·docx·pptx·md)가 diff 단위를 정하고, 문서 정의의 fmt가 저장 형식을 정한다.
  docx 블록 모델은 fmt="pdf"(텍스트 PDF, 비임베드 CID 폰트 + ToUnicode) · "hwpx"(OWPML zip) · "txt"로도 저장한다. 표준 라이브러리만 쓴다.
승인자: 소유 팀 팀장. 팀장이 작성하면 같은 팀 대리 승인자(P.DEPUTY)가 승인하고, 팀장 부재 시 변경에 approver를 지정한다(본인 승인 금지).

버전 엔진: 모든 문서를 v1으로 만든 뒤 CHANGES를 날짜순으로 적용한다.
  승인 → <프로젝트>/v{n}/ 에 그 문서의 새 HEAD 버전 생성
  승인 대기 → <프로젝트>/승인대기/, 반려 → <프로젝트>/반려/ 에 제출 파일만 생성 (HEAD 그대로)
  변경 전후 내용을 셀 단위로 비교해 diff 정답을 만들고, WATCH 정규식으로 반복값 위치를 자동 검출한다.

출력: 1_문서세트/(인원풀, <프로젝트>/문서·문서이력) · 2_질문셋/(질문셋) · 3_변경시나리오/(변경 예시·영향 라벨)

실행: python build_docset.py
"""
import copy
import re
import shutil
import zipfile
import zlib
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches
from pptx.util import Pt as PPt

import company
import project_a
import project_b
import questions
import train_a
import train_b

ROOT = Path(__file__).parent
DOC_DIR, Q_DIR, SCN_DIR = ROOT / "1_문서세트", ROOT / "2_질문셋", ROOT / "3_변경시나리오"  # DATA-01 / DATA-07 / DATA-03
FONT = "맑은 고딕"
PROJECTS = [project_a, project_b]
TRAIN = {"A": train_a.SCENARIOS, "B": train_b.SCENARIOS}
TRAIN_DOC = {"A": train_a.__doc__, "B": train_b.__doc__}  # 학습용 변경 시나리오(DATA-06 초안)
KINDS = ("값 변경", "항목 추가", "항목 삭제", "흐름 변경", "표현 수정", "여러 곳 변경")  # 시나리오 유형. 여러 곳 변경 = 서로 다른 변경 여러 개를 한 번에 제출
EMP = {e[0]: e for e in company.EMPLOYEES}
EXT = {x[0]: x for p in PROJECTS for x in p.EXTERNAL}


def pname(pid):
    return (EMP.get(pid) or EXT[pid])[1]


def teams(P):
    return P.TEAMS + [P.PMO]


def team_name(P):
    return {t[0]: t[1] for t in teams(P)}


def lead(P):
    return {t[0]: t[2] for t in teams(P)}


def deputy(P):
    return getattr(P, "DEPUTY", {})


def approver_of(P, team, author, override=None):
    """승인 담당: 지정(팀장 부재 등) > 작성자가 팀장이면 대리 승인자 > 팀장."""
    if override:
        return override
    return deputy(P)[team] if author == lead(P)[team] else lead(P)[team]


def apv_kind(P, team, author, apv):
    if apv == lead(P)[team]:
        return "팀장"
    return "대리 승인(작성자=팀장)" if author == lead(P)[team] else "대리 승인(팀장 부재)"


def in_team(P, pid, team):
    t = next(x for x in teams(P) if x[0] == team)
    return pid == t[2] or pid in t[3]


def roster(P):
    """사번 → (팀 코드, 역할). 오너 > 팀장 > 멤버 > 게스트. 명단에 없는 사내 직원은 '프로젝트 밖'."""
    r = {}
    dp = set(deputy(P).values())
    for code, _, ld, members, _ in teams(P):
        r[ld] = (code, "팀장")
        for m in members:
            r[m] = (code, "멤버(대리 승인)" if m in dp else "멤버")
    r[P.OWNER] = ("PMO", "오너")
    for x in P.GUESTS:
        r[x] = ("-", "게스트")
    return r


# ─────────────────────────── 문서 모델 (데이터 → 표/블록) ───────────────────────────
# xlsx: [(시트명, 제목, 헤더, 행, 열너비, 키 열 인덱스)]   docx: [("h1"|"h2"|"p", 텍스트) | ("table", 행, 헤더여부)]
# pptx: {"list": 화면 목록 행, "screens": SCR}         md: 문자열

def split_ids(s):
    return [x for x in s.split(", ") if x and x != "-"]


def m_req(P, d, s):
    tn = team_name(P)
    FR, SCR, IF, TC = d["FR"], d["SCR"], d["IF"], d["TC"]
    scr_if = {x[0]: x[5] for x in SCR}
    if_tb = {i[0]: i[9] for i in IF}
    rtm = []
    for f in FR:
        steps = [(p[0], st) for p in d["PROC"] for st in p[4] if st[4] == f[0]]
        scrs = split_ids(f[9])
        ifs = sorted({i for sc in scrs for i in scr_if[sc]} | {i for _, st in steps for i in split_ids(st[5])})
        tbs = sorted({t for i in ifs for t in if_tb[i]})
        tcs = [t[0] for t in TC if f[0] in split_ids(t[2])]
        rtm.append((f[0], f[2], ", ".join(sorted({p for p, _ in steps})) or "-", ", ".join(scrs), ", ".join(ifs), ", ".join(tbs),
                    ", ".join(tcs) or "-", tn[f[10]]))
    return "xlsx", [
        ("1. 용어·역할", "1. 용어 및 역할 정의", ["구분", "용어/역할", "정의", "비고"], d["ROLES"], (8, 14, 70, 22), (0, 1)),
        ("2. 기능 요구사항", "2. 기능 요구사항",
         ["요구사항 ID", "대분류", "요구사항명", "상세 설명", "사용자", "선행 조건", "처리 결과 / 수용 기준", "예외 처리", "우선순위", "관련 화면", "담당 개발팀", "출처", "상태"],
         [f[:10] + (tn[f[10]], f[11], "확정") for f in FR], (11, 10, 18, 60, 8, 16, 40, 40, 8, 16, 16, 22, 8), (0,)),
        ("3. 권한 매트릭스", "3. 역할별 권한 매트릭스 (O 가능 · △ 조건부 · X 불가)", ["요구사항 ID", "기능", *P.PERM_ROLES, "조건·비고"],
         [(p[0], next(f[2] for f in FR if f[0] == p[0]), *p[1:]) for p in d["PERM"]], (11, 22, *[9] * len(P.PERM_ROLES), 34), (0,)),
        ("4. 비기능 요구사항", "4. 비기능 요구사항", ["요구사항 ID", "분류", "요구사항명", "상세 설명", "측정 지표", "목표 수치", "검증 방법", "우선순위", "관련 FR"],
         d["NFR"], (11, 9, 20, 50, 18, 14, 14, 8, 16), (0,)),
        ("5. 미결 사항", "5. 미결 사항 (정책 결정 필요)", ["No", "이슈", "선택지", "영향 받는 요구사항", "결정자", "결정 기한", "결정 내용", "상태"],
         d["OPEN_ISSUES"], (5, 24, 28, 18, 18, 12, 30, 8), (0,)),
        ("6. 요구사항 추적표", "6. 요구사항 추적표(RTM) — 요구사항 → 업무 프로세스 → 화면 → 인터페이스 → 테이블 → 테스트케이스",
         ["요구사항 ID", "요구사항명", "업무 프로세스", "화면", "인터페이스(화면·프로세스 경유)", "테이블", "테스트케이스", "담당 개발팀"], rtm,
         (11, 20, 12, 18, 36, 44, 18, 16), (0,)),
    ]


def m_proc(P, d, s):
    tn = team_name(P)
    b = [("h1", "1. 개요"),
         ("p", P.PROC_INTRO),
         ("h1", "2. 프로세스 목록"),
         ("table", [["프로세스 ID", "프로세스명", "담당 개발팀", "관련 요구사항"]] +
          [[p[0], p[1], tn[p[2]], ", ".join(sorted({st[4] for st in p[4]}))] for p in d["PROC"]], True),
         ("h1", "3. 프로세스 상세")]
    for pid, name, _, asis, steps, rules, exs in d["PROC"]:
        b += [("h2", f"{pid} {name}"), ("p", "As-Is(현행)"), ("p", asis), ("p", "To-Be 업무 흐름"),
              ("table", [["No", "단계", "수행자", "시스템", "관련 요구사항", "관련 인터페이스"]] + [list(st) for st in steps], True),
              ("p", "업무 규칙"), ("table", [["규칙 ID", "내용"]] + [list(r) for r in rules], True),
              ("p", "예외 흐름"), ("table", [["예외 ID", "상황", "처리"]] + [list(e) for e in exs], True)]
    return "docx", b


def m_scr(P, d, s):
    tn = team_name(P)
    return "pptx", {"list": [[c[0], c[1], c[2], c[3], ", ".join(c[4]), tn[c[7]]] for c in d["SCR"]], "screens": d["SCR"], "team": tn}


def m_ui(P, d, s):
    scr = {x[0]: x[1] for x in d["SCR"]}
    return "xlsx", [
        ("1. 공통 컴포넌트", "1. 공통 컴포넌트 규칙", ["컴포넌트 ID", "컴포넌트", "규칙·문구", "적용 화면"], d["UI_CMP"], (12, 16, 70, 34), (0,)),
        ("2. 퍼블리싱 목록", f"2. 화면별 퍼블리싱 목록 ({P.ASOF} 기준)", ["화면 ID", "화면명", "퍼블리싱 파일", "담당", "상태", "완료(예정)일"],
         [(u[0], scr[u[0]], u[1], pname(u[2]), u[3], u[4]) for u in d["UI_PUB"]], (10, 22, 26, 10, 8, 14), (0,)),
    ]


def if_detail(items):
    b = []
    for (iid, iname, kind, method, path, snd, rcv, cycle, scrs, tbs, req, resp, errs, _) in items:
        b += [("h2", f"{iid} {iname}"),
              ("table", [["IF ID", iid, "유형", kind], ["방식", method, "경로/대상", path], ["송신", snd, "수신", rcv],
                         ["주기", cycle, "관련 화면", ", ".join(scrs) or "-"], ["관련 테이블", ", ".join(tbs), "", ""]], False),
              ("p", "요청 항목"), ("table", [["항목명", "타입", "필수", "설명"]] + [list(f) for f in req], True),
              ("p", "응답 항목"), ("table", [["항목명", "타입", "필수", "설명"]] + [list(f) for f in resp], True)]
        if errs:
            b += [("p", "오류·예외 처리"), ("table", [["코드", "내용"]] + [list(e) for e in errs], True)]
    return b


def m_if(P, d, s):
    items = [i for i in d["IF"] if i[13] == s["team"]]
    b = [("h1", "1. 개요"), ("p", P.IF_INTRO[s["team"]])]
    if s.get("eif"):
        b += [("h1", "2. 연계 대상 시스템"), ("table", [["대상 시스템", "소유·위치", "연계 방식", "관련 IF"]] + [list(x) for x in d["EIF_SYSTEMS"]], True),
              ("h1", "3. 연계 공통 사항"), ("table", [["항목", "내용"]] + [list(x) for x in d["EIF_COMMON"]], True)]
    n = len([x for x in b if x[0] == "h1"])
    b += [("h1", f"{n + 1}. 인터페이스 목록"),
          ("table", [["IF ID", "인터페이스명", "유형", "방식", "경로/대상", "관련 화면"]] + [[i[0], i[1], i[2], i[3], i[4], ", ".join(i[8]) or "-"] for i in items], True),
          ("h1", f"{n + 2}. 인터페이스 상세")] + if_detail(items)
    return "docx", b


def m_blocks(P, d, s):
    return "docx", d[s["data"]]


def m_tb(P, d, s):
    tn = team_name(P)
    used_by = {t[0]: [i[0] for i in d["IF"] if t[0] in i[9]] for t in d["TB"]}
    return "xlsx", [
        ("1. 테이블 목록", f"1. 테이블 목록 ({P.DB_DESC})", ["No", "테이블명", "테이블 한글명", "설명", "담당 업무팀", "관련 인터페이스"],
         [(n, t[0], t[1], t[2], tn[t[4]], ", ".join(used_by[t[0]])) for n, t in enumerate(d["TB"], 1)], (5, 22, 14, 40, 18, 50), (1,)),
        ("2. 컬럼 정의", "2. 컬럼 정의", ["테이블명", "테이블 한글명", "No", "컬럼명", "컬럼 한글명", "데이터 타입", "NULL", "키", "기본값", "설명"],
         [(t[0], t[1], n, *c) for t in d["TB"] for n, c in enumerate(t[3], 1)], (22, 12, 5, 18, 18, 14, 6, 7, 12, 44), (0, 3)),
        ("3. 공통코드", "3. 공통코드", ["코드그룹", "코드그룹명", "코드", "코드명", "정렬", "비고"], d["CODES"], (12, 12, 18, 16, 6, 30), (0, 2)),
    ]


def m_erd(P, d, s):
    rels, ents = [], []
    for t in d["TB"]:
        keyed = [c for c in t[3] if c[4]]
        ents.append(f"  {t[0]} {{\n" + "".join(f"    {c[2].split('(')[0]} {c[0]} {c[4].replace(',', '_')}\n" for c in keyed) + "  }")
        for c in t[3]:
            if "FK" in c[4]:
                parent = c[6].split(".")[0]
                card = "1:0..1" if "UK" in c[4] else "1:N"
                rels.append((parent, t[0], c[0], card, "선택" if c[3] == "Y" else "필수"))
    mer = {("1:N", "필수"): "||--o{", ("1:N", "선택"): "|o--o{", ("1:0..1", "필수"): "||--o|", ("1:0..1", "선택"): "|o--o|"}
    lines = [f"  {p} {mer[(cd, opt)]} {c} : \"{col}\"" for p, c, col, cd, opt in rels]
    text = (f"테이블정의서의 PK·FK·UK로 그린 논리 ERD. 테이블 {len(d['TB'])}개, 관계 {len(rels)}개.\n\n"
            "## 1. 다이어그램\n\n```mermaid\nerDiagram\n" + "\n".join(lines) + "\n" + "\n".join(ents) + "\n```\n\n"
            "## 2. 관계 목록\n\n| 부모 테이블 | 자식 테이블 | FK 컬럼 | 카디널리티 | 참조 |\n|---|---|---|---|---|\n" +
            "".join(f"| {p} | {c} | {col} | {cd} | {opt} |\n" for p, c, col, cd, opt in rels))
    return "md", text


def m_tc(P, d, s):
    summ = {}
    for t in d["TC"]:
        summ.setdefault(t[1], {}).setdefault(t[8], 0)
        summ[t[1]][t[8]] += 1
    return "xlsx", [
        ("1. 테스트케이스", f"1. 테스트케이스 및 수행 결과 ({P.ASOF} 기준)",
         ["TC ID", "단계", "관련 요구사항", "관련 화면·IF", "시나리오", "입력·조건", "기대 결과", "담당", "수행 결과", "수행일", "결함 ID"],
         [t[:7] + (pname(t[7]),) + t[8:] for t in d["TC"]], (8, 6, 12, 18, 22, 36, 40, 8, 9, 12, 9), (0,)),
        ("2. 결함 목록", "2. 결함 목록", ["결함 ID", "TC", "발견일", "심각도", "내용", "원인 구분", "조치 팀", "조치 상태"],
         d["DEFECTS"], (9, 8, 12, 7, 50, 44, 18, 18), (0,)),
        ("3. 수행 요약", "3. 단계별 수행 요약", ["단계", "수행 결과", "건수"],
         [(k, r, n) for k, v in summ.items() for r, n in sorted(v.items())], (10, 10, 8), (0, 1)),
    ]


def m_wbs(P, d, s):
    return "xlsx", [
        ("1. WBS", f"1. WBS ({P.ASOF} 기준)", ["WBS ID", "단계", "작업", "담당 팀", "산출물", "시작", "종료", "진척률", "상태"], d["WBS"],
         (7, 8, 40, 26, 40, 12, 12, 8, 8), (0,)),
        ("2. 검수 마일스톤", "2. 검수 마일스톤", ["ID", "마일스톤", "예정일", "검수자", "검수 대상 산출물", "상태"], d["MILESTONES"], (5, 16, 12, 30, 70, 20), (0,)),
    ]


MODELS = {"req": m_req, "proc": m_proc, "scr": m_scr, "ui": m_ui, "if": m_if, "blocks": m_blocks, "tb": m_tb, "erd": m_erd, "tc": m_tc, "wbs": m_wbs}

# ─────────────────────────── 렌더러 ───────────────────────────
THIN = Side(style="thin", color="999999")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEAD_FILL = PatternFill("solid", fgColor="DCE6F1")
WRAP = Alignment(wrap_text=True, vertical="top")


def cover_rows(meta):
    return [("프로젝트명", meta["project"]), ("발주처", meta["client"]), ("수행사", company.COMPANY), ("작성 팀", meta["team"]),
            ("문서 버전", meta["version"]), ("문서 상태", meta["state"]), ("공개 범위", meta["grade"]), ("최초 작성일", meta["date"]),
            ("작성자", meta["author"]), ("검토자", meta["reviewer"]), ("승인자", meta["approver"])]


HIST_HEAD = ["버전", "일자", "변경 내용", "작성자", "승인자"]


def xl_sheet(wb, title, heading, header, rows, widths):
    ws = wb.create_sheet(title)
    ws["A1"] = heading
    ws["A1"].font = Font(name=FONT, bold=True, size=13)
    ws.append([])
    ws.append(header)
    for row in rows:
        ws.append(list(row))
    for r in ws.iter_rows(min_row=3, max_row=ws.max_row):
        for c in r:
            c.border, c.alignment = BOX, WRAP
            c.font = Font(name=FONT, size=10, bold=c.row == 3)
            if c.row == 3:
                c.fill = HEAD_FILL
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A4"


def render_xlsx(path, meta, sheets):
    wb = Workbook()
    ws = wb.active
    ws.title = "표지"
    for r in [[meta["name"]]] + [list(x) for x in cover_rows(meta)] + [[], ["개정 이력"], HIST_HEAD] + [list(h) for h in meta["history"]] + \
             [[], ["시트 구성"]] + [[s[0], s[1]] for s in sheets]:
        ws.append(r)
    ws["A1"].font = Font(name=FONT, bold=True, size=16)
    for w, col in zip((16, 40, 44, 12, 12), "ABCDE"):
        ws.column_dimensions[col].width = w
    cache = {}  # (시트명, 셀) → 수식 계산값. Excel 저장본처럼 캐시 값을 넣어 data_only 읽기도 값이 나오게 한다
    for s in sheets:
        fn = MESSY.get(s[0]) if meta.get("xl") == "messy" else None
        if fn:
            fn(wb, s, meta, cache)
        else:
            xl_sheet(wb, *s[:5])
    wb.calculation.fullCalcOnLoad = True
    wb.save(path)
    if cache:
        _inject_cached(path, wb.sheetnames, cache)


# ── 파싱 난이도 높은 xlsx(meta xl="messy"): 병합 셀·2단 헤더·소계 수식·날짜 셀·숨김 열·시트 간 COUNTIFS ──
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
SUB_FILL = PatternFill("solid", fgColor="F2F2F2")


def _d(s):
    import datetime
    return datetime.date.fromisoformat(s)


def _style(ws, r1, r2, ncol, head_rows=()):
    for row in ws.iter_rows(min_row=r1, max_row=r2, max_col=ncol):
        for c in row:
            c.border = BOX
            c.font = Font(name=FONT, size=10, bold=c.row in head_rows)
            if c.row in head_rows:
                c.fill, c.alignment = HEAD_FILL, CENTER
            elif c.alignment.horizontal is None:
                c.alignment = WRAP


def xl_wbs_messy(wb, s, meta, cache):
    """1. WBS: 제목·기준일 병합, 2단 헤더(일정=시작/종료), 단계 세로 병합, 단계별 소계 행(SUM·AVERAGE), 전체 행, 숨김 가중치 열."""
    title, rows = s[0], s[3]
    ws = wb.create_sheet(title)
    ws.merge_cells("A1:J1")
    ws["A1"] = f"{meta['project']} — WBS 일정표"
    ws["A1"].font = Font(name=FONT, bold=True, size=14)
    ws.merge_cells("A2:J2")
    ws["A2"] = f"기준일: {s[1].split('(')[-1].rstrip(')')}  |  문서 버전 {meta['version']}  |  진척률은 실적 기준, 소계는 단계 평균"
    for col, h in zip("ABCDE", ["WBS ID", "단계", "작업", "담당 팀", "산출물"]):
        ws[f"{col}4"] = h
        ws.merge_cells(f"{col}4:{col}5")
    ws["F4"] = "일정"
    ws.merge_cells("F4:G4")
    ws["F5"], ws["G5"] = "시작", "종료"
    for col, h in zip("HIJK", ["기간(일)", "진척률", "상태", "가중치"]):
        ws[f"{col}4"] = h
        ws.merge_cells(f"{col}4:{col}5")
    r, subs, data_rows = 6, [], []
    runs = []
    for row in rows:  # 연속된 같은 단계끼리 묶는다(떨어져 있으면 별도 묶음)
        if runs and runs[-1][0] == row[1]:
            runs[-1][1].append(row)
        else:
            runs.append((row[1], [row]))
    for stage, items in runs:
        first = r
        for wid, _st, task, team, out, start, end, prog, state in items:
            p = int(prog.rstrip("%")) / 100
            days = (_d(end) - _d(start)).days + 1
            ws.append([wid, stage if r == first else None, task, team, out, _d(start), _d(end), f"=G{r}-F{r}+1", p, state, f"=H{r}*I{r}"])
            cache[(title, f"H{r}")], cache[(title, f"K{r}")] = days, days * p
            ws[f"F{r}"].number_format = ws[f"G{r}"].number_format = "yyyy-mm-dd"
            ws[f"I{r}"].number_format = "0%"
            data_rows.append((r, days, p))
            r += 1
        last = r - 1
        if last > first:
            ws.merge_cells(f"B{first}:B{last}")
        ws[f"B{first}"].alignment = CENTER
        part = data_rows[-len(items):]
        ws.append([None, f"소계({stage})", None, None, None, None, None, f"=SUM(H{first}:H{last})", f"=AVERAGE(I{first}:I{last})", None,
                   f"=SUM(K{first}:K{last})"])
        ws.merge_cells(f"B{r}:G{r}")
        cache[(title, f"H{r}")] = sum(x[1] for x in part)
        cache[(title, f"I{r}")] = sum(x[2] for x in part) / len(part)
        cache[(title, f"K{r}")] = sum(x[1] * x[2] for x in part)
        ws[f"I{r}"].number_format = "0%"
        subs.append(r)
        r += 1
    ws.append([None, "전체(기간 가중 진척률)", None, None, None, None, None, "=" + "+".join(f"H{x}" for x in subs),
               "=(" + "+".join(f"K{x}" for x in subs) + f")/H{r}", None, "=" + "+".join(f"K{x}" for x in subs)])
    ws.merge_cells(f"B{r}:G{r}")
    tot_h, tot_k = sum(x[1] for x in data_rows), sum(x[1] * x[2] for x in data_rows)
    cache[(title, f"H{r}")], cache[(title, f"I{r}")], cache[(title, f"K{r}")] = tot_h, tot_k / tot_h, tot_k
    ws[f"I{r}"].number_format = "0.0%"
    _style(ws, 4, r, 11, head_rows=(4, 5))
    for x in subs + [r]:
        for c in ws[x][:11]:
            c.fill, c.font = SUB_FILL, Font(name=FONT, size=10, bold=True)
    for col, w in zip("ABCDEFGHIJK", (7, 8, 40, 24, 34, 11, 11, 8, 8, 8, 8)):
        ws.column_dimensions[col].width = w
    ws.column_dimensions["K"].hidden = True
    ws.freeze_panes = "C6"


def xl_tc_summary_messy(wb, s, meta, cache):
    """3. 수행 요약: 단계 × 결과 피벗을 '1. 테스트케이스' 시트 COUNTIFS로 계산, 결과 헤더 병합, 합계 행·Pass율."""
    title = s[0]
    ws = wb.create_sheet(title)
    ws.merge_cells("A1:G1")
    ws["A1"] = "3. 단계별 수행 요약 (수식: '1. 테스트케이스' 시트 집계)"
    ws["A1"].font = Font(name=FONT, bold=True, size=13)
    ws["A3"] = "단계"
    ws.merge_cells("A3:A4")
    ws["B3"] = "수행 결과(건)"
    ws.merge_cells("B3:E3")
    ws["F3"], ws["G3"] = "합계", "Pass율"
    ws.merge_cells("F3:F4")
    ws.merge_cells("G3:G4")
    results = ["Pass", "Fail", "Block", "미수행"]
    for col, h in zip("BCDE", results):
        ws[f"{col}4"] = h
    cnt = {}
    for st, res, n in s[3]:
        cnt[(st, res)] = n
    stages = list(dict.fromkeys(st for st, _, _ in s[3]))
    src = "'1. 테스트케이스'"
    r = 5
    for st in stages:
        ws[f"A{r}"] = st
        for col, res in zip("BCDE", results):
            ws[f"{col}{r}"] = f'=COUNTIFS({src}!$B:$B,$A{r},{src}!$I:$I,{col}$4)'
            cache[(title, f"{col}{r}")] = cnt.get((st, res), 0)
        tot = sum(cnt.get((st, x), 0) for x in results)
        ws[f"F{r}"], ws[f"G{r}"] = f"=SUM(B{r}:E{r})", f"=IFERROR(B{r}/(F{r}-E{r}),0)"
        done = tot - cnt.get((st, "미수행"), 0)
        cache[(title, f"F{r}")], cache[(title, f"G{r}")] = tot, (cnt.get((st, "Pass"), 0) / done if done else 0)
        ws[f"G{r}"].number_format = "0.0%"
        r += 1
    ws[f"A{r}"] = "합계"
    for col in "BCDEF":
        ws[f"{col}{r}"] = f"=SUM({col}5:{col}{r - 1})"
        cache[(title, f"{col}{r}")] = sum(cache[(title, f"{col}{x}")] for x in range(5, r))
    ws[f"G{r}"] = f"=IFERROR(B{r}/(F{r}-E{r}),0)"
    done = cache[(title, f"F{r}")] - cache[(title, f"E{r}")]
    cache[(title, f"G{r}")] = cache[(title, f"B{r}")] / done if done else 0
    ws[f"G{r}"].number_format = "0.0%"
    _style(ws, 3, r, 7, head_rows=(3, 4))
    for c in ws[r][:7]:
        c.fill, c.font = SUB_FILL, Font(name=FONT, size=10, bold=True)
    ws[f"A{r + 2}"] = "※ Pass율 = Pass ÷ (합계 − 미수행). 결과 열은 '1. 테스트케이스' 시트가 바뀌면 다시 계산된다."
    for col, w in zip("ABCDEFG", (10, 9, 9, 9, 9, 9, 10)):
        ws.column_dimensions[col].width = w


MESSY = {"1. WBS": xl_wbs_messy, "3. 수행 요약": xl_tc_summary_messy}


def _inject_cached(path, sheetnames, cache):
    """openpyxl은 수식 셀의 계산값(<v>)을 비워 둔다 → 계산해 둔 값을 XML에 채운다(Excel 저장본과 같은 형태)."""
    idx = {n: i for i, n in enumerate(sheetnames, 1)}
    with zipfile.ZipFile(path) as z:
        items = [(i, z.read(i.filename)) for i in z.infolist()]
    for name in {k[0] for k in cache}:
        target = f"xl/worksheets/sheet{idx[name]}.xml"
        for n, (info, data) in enumerate(items):
            if info.filename != target:
                continue
            xml = data.decode("utf-8")

            def fill(m):
                v = cache.get((name, m.group(1)))
                if v is None:
                    return m.group(0)
                return f'<c r="{m.group(1)}"{m.group(2)}><f>{m.group(3)}</f><v>{round(v, 10)}</v></c>'
            xml = re.sub(r'<c r="([A-Z]+\d+)"([^>]*)><f>(.*?)</f><v\s*/?>(?:</v>)?</c>', fill, xml)
            items[n] = (info, xml.encode("utf-8"))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in items:
            z.writestr(info, data)


def render_docx(path, meta, blocks):
    doc = Document()
    st = doc.styles["Normal"]
    st.font.name, st.font.size = FONT, Pt(10)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

    def tbl(rows, head=True):
        t = doc.add_table(rows=len(rows), cols=len(rows[0]))
        t.style = "Table Grid"
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                t.cell(i, j).text = str(v)
                if head and i == 0 and t.cell(i, j).paragraphs[0].runs:
                    t.cell(i, j).paragraphs[0].runs[0].bold = True
        doc.add_paragraph()

    doc.add_heading(f"{meta['project']}\n{meta['name']}", 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    tbl([["항목", "내용"]] + [list(x) for x in cover_rows(meta)])
    doc.add_heading("개정 이력", 1)
    tbl([HIST_HEAD] + [list(h) for h in meta["history"]])
    for b in blocks:
        if b[0] == "h1":
            doc.add_heading(b[1], 1)
        elif b[0] == "h2":
            doc.add_heading(b[1], 2)
        elif b[0] == "p":
            doc.add_paragraph(b[1])
        else:
            tbl(b[1], b[2])
    doc.save(path)


def render_pptx(path, meta, body):
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]

    def text(slide, x, y, w, h, s, size=12, bold=False):
        tf = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
        tf.word_wrap = True
        tf.text = s
        for p in tf.paragraphs:
            for r in p.runs:
                r.font.size, r.font.bold, r.font.name = PPt(size), bold, FONT

    def table(slide, x, y, w, rows, col_w, size=10, head=True):
        t = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(0.3 * len(rows))).table
        for j, cw in enumerate(col_w):
            t.columns[j].width = Inches(cw)
        for i, row in enumerate(rows):
            for j, v in enumerate(row):
                cell = t.cell(i, j)
                cell.text = str(v)
                for p in cell.text_frame.paragraphs:
                    for r in p.runs:
                        r.font.size, r.font.name, r.font.bold = PPt(size), FONT, head and i == 0

    s = prs.slides.add_slide(blank)
    text(s, 1, 1.2, 11, 1, f"{meta['project']}\n{meta['name']}", 30, True)
    table(s, 1, 3.0, 8, [["항목", "내용"]] + [list(x) for x in cover_rows(meta)], (2.5, 5.5))
    s = prs.slides.add_slide(blank)
    text(s, 0.5, 0.3, 12, 0.6, "개정 이력", 20, True)
    table(s, 0.5, 1.1, 12.3, [HIST_HEAD] + [list(h) for h in meta["history"]], (1.2, 1.6, 6.5, 1.5, 1.5))
    s = prs.slides.add_slide(blank)
    text(s, 0.5, 0.3, 12, 0.6, "화면 목록", 20, True)
    table(s, 0.5, 1.0, 12.3, [["화면 ID", "화면명", "경로(URL)", "사용자", "관련 요구사항", "담당 개발팀"]] + body["list"], (1.3, 2.6, 3.3, 1.2, 2.2, 1.7), size=9)
    for sid, sname, path_, user, frs, ifs, comps, team in body["screens"]:
        s = prs.slides.add_slide(blank)
        text(s, 0.4, 0.2, 12, 0.5, f"{sid}  {sname}", 20, True)
        table(s, 0.4, 0.75, 12.5, [["화면 ID", sid, "화면명", sname, "경로(URL)", path_],
                                   ["사용자", user, "관련 요구사항", ", ".join(frs), "관련 인터페이스", ", ".join(ifs)],
                                   ["담당 개발팀", body["team"][team], "", "", "", ""]],
              (1.2, 1.6, 1.4, 2.6, 1.5, 4.2), size=10, head=False)
        frame = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.4), Inches(1.8), Inches(6.2), Inches(5.4))
        frame.fill.background()
        frame.line.color.rgb = RGBColor(0x88, 0x88, 0x88)
        h = min(0.7, 5.0 / len(comps))
        for n, (label, _) in enumerate(comps, 1):
            box = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(2.0 + (n - 1) * (h + 0.05)), Inches(5.6), Inches(h))
            box.fill.solid()
            box.fill.fore_color.rgb = RGBColor(0xF2, 0xF2, 0xF2)
            box.line.color.rgb = RGBColor(0xAA, 0xAA, 0xAA)
            box.text_frame.text = f"({n}) {label}"
            for r in box.text_frame.paragraphs[0].runs:
                r.font.size, r.font.name, r.font.color.rgb = PPt(11), FONT, RGBColor(0x33, 0x33, 0x33)
        text(s, 6.9, 1.75, 6, 0.4, "Description", 13, True)
        table(s, 6.9, 2.2, 6.0, [["No", "항목", "설명"]] + [[n, lb, ds] for n, (lb, ds) in enumerate(comps, 1)], (0.5, 1.9, 3.6), size=10)
    prs.save(path)


def render_md(path, meta, body):
    head = f"# {meta['project']} — {meta['name']}\n\n| 항목 | 내용 |\n|---|---|\n" + "".join(f"| {k} | {v} |\n" for k, v in cover_rows(meta))
    hist = "\n## 개정 이력\n\n| " + " | ".join(HIST_HEAD) + " |\n|---|---|---|---|---|\n" + "".join("| " + " | ".join(h) + " |\n" for h in meta["history"])
    path.write_text(head + hist + "\n" + body, encoding="utf-8")


def full_blocks(meta, blocks):
    """docx 외 형식(pdf·hwpx·txt)용: 표지·개정 이력을 블록 앞에 붙인다."""
    return ([("title", f"{meta['project']}\n{meta['name']}"), ("table", [["항목", "내용"]] + [list(x) for x in cover_rows(meta)], True),
             ("h1", "개정 이력"), ("table", [HIST_HEAD] + [list(h) for h in meta["history"]], True)] + list(blocks))


def render_txt(path, meta, blocks):
    L = []
    for b in full_blocks(meta, blocks):
        if b[0] == "title":
            L += [b[1].replace("\n", " — "), "=" * 60]
        elif b[0] in ("h1", "h2"):
            L += ["", b[1], ("=" if b[0] == "h1" else "-") * 40]
        elif b[0] == "p":
            L.append(b[1])
        else:
            L += [" | ".join(str(v) for v in r) for r in b[1]] + [""]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


# PDF: 한글 폰트를 임베드하지 않고 Adobe-Korea1 CID 폰트(HYGoThic-Medium)를 참조한다 → OS별 폰트 경로 불필요, 파일 작음.
# 문자 코드 = UCS-2이고 ToUnicode CMap을 넣어 텍스트 추출(pypdf·pdfminer)이 정확하다. ASCII 폭 500, 그 외 1000.
PDF_W, PDF_H, PDF_M = 595.28, 841.89, 48
PDF_FIX = str.maketrans({"−": "-", "—": "-", "‐": "-", "–": "-"})


def _pdf_s(s):
    return "".join(c if ord(c) < 0xD800 or 0xE000 <= ord(c) < 0x10000 else "?" for c in str(s).translate(PDF_FIX))


def _pw(s, size):
    return sum(0.5 if ord(c) < 128 else 1.0 for c in s) * size


def _wrap(s, size, width):
    out = []
    for para in _pdf_s(s).split("\n"):
        line = ""
        for ch in para:
            if line and _pw(line + ch, size) > width:
                out.append(line)
                line = ""
            line += ch
        out.append(line)
    return out


def render_pdf(path, meta, blocks, shuffle=False):
    """shuffle=True: 보이는 모습은 같고 페이지 안 텍스트 그리기 순서만 뒤집는다(추출 순서 흔들림 케이스, diff_cases.py)."""
    pages, ops = [], []
    y = PDF_H - PDF_M

    def text(x, yy, s, size):
        ops.append(f"BT /F1 {size} Tf {x:.1f} {yy:.1f} Td <{_pdf_s(s).encode('utf-16-be').hex()}> Tj ET")

    def need(h):
        nonlocal ops, y
        if y - h < PDF_M + 16:
            pages.append(ops)
            ops, y = [], PDF_H - PDF_M

    def para(s, size, before=0, after=4):
        nonlocal y
        y -= before
        for line in _wrap(s, size, PDF_W - 2 * PDF_M):
            need(size * 1.5)
            y -= size * 1.5
            text(PDF_M, y + size * 0.3, line, size)
        y -= after

    def table(rows, head, size=8):
        nonlocal y
        n = max(len(r) for r in rows)
        rows = [[str(v) for v in r] + [""] * (n - len(r)) for r in rows]
        want = [min(max(_pw(r[j], size) for r in rows), 200) + 10 for j in range(n)]
        cw = [w * (PDF_W - 2 * PDF_M) / sum(want) for w in want]
        pad, lead = 3, size * 1.35
        for i, r in enumerate(rows):
            cells = [_wrap(v, size, cw[j] - 2 * pad) for j, v in enumerate(r)]
            h = max(len(c) for c in cells) * lead + 2 * pad
            need(h)
            x = PDF_M
            for j, c in enumerate(cells):
                if head and i == 0:
                    ops.append(f"0.86 0.9 0.95 rg {x:.1f} {y - h:.1f} {cw[j]:.1f} {h:.1f} re f 0 g")
                ops.append(f"0.5 w {x:.1f} {y - h:.1f} {cw[j]:.1f} {h:.1f} re S")
                for k, line in enumerate(c):
                    text(x + pad, y - pad - (k + 1) * lead + size * 0.35, line, size)
                x += cw[j]
            y -= h
        y -= 8

    for b in full_blocks(meta, blocks):
        if b[0] == "title":
            para(b[1], 17, 40, 24)
        elif b[0] == "h1":
            para(b[1], 13, 10, 4)
        elif b[0] == "h2":
            para(b[1], 11, 6, 3)
        elif b[0] == "p":
            para(b[1], 9.5)
        else:
            table(b[1], b[2])
    pages.append(ops)
    if shuffle:  # 칸 배경·테두리를 먼저, 텍스트는 역순으로 — 겹치는 영역이 없어 화면은 같다
        pages = [[o for o in pg if not o.startswith("BT")] + [o for o in pg if o.startswith("BT")][::-1] for pg in pages]

    objs = [None, None]

    def add(body, stream=None):
        if stream is not None:
            body = body + f" /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        objs.append(body if isinstance(body, bytes) else body.encode())
        return len(objs)

    cmap = ("/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
            "/CMapName /Adobe-Identity-UCS def\n/CMapType 2 def\n1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n")
    hi = [h for h in range(256) if not 0xD8 <= h <= 0xDF]
    for i in range(0, len(hi), 100):
        part = hi[i:i + 100]
        cmap += f"{len(part)} beginbfrange\n" + "".join(f"<{h:02X}00> <{h:02X}FF> <{h:02X}00>\n" for h in part) + "endbfrange\n"
    cmap += "endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend\n"
    tu = add(b"<<", cmap.encode())
    fd = add("<< /Type /FontDescriptor /FontName /HYGoThic-Medium /Flags 4 /FontBBox [-6 -145 1003 880] /ItalicAngle 0 "
             "/Ascent 880 /Descent -120 /CapHeight 880 /StemV 93 >>")
    cid = add(f"<< /Type /Font /Subtype /CIDFontType0 /BaseFont /HYGoThic-Medium /CIDSystemInfo << /Registry (Adobe) /Ordering (Korea1) "
              f"/Supplement 1 >> /FontDescriptor {fd} 0 R /DW 1000 /W [1 95 500] >>")
    f1 = add(f"<< /Type /Font /Subtype /Type0 /BaseFont /HYGoThic-Medium-UniKS-UCS2-H /Encoding /UniKS-UCS2-H "
             f"/DescendantFonts [{cid} 0 R] /ToUnicode {tu} 0 R >>")
    kids = []
    for n, pg in enumerate(pages, 1):
        foot = f"BT /F1 7.5 Tf {PDF_M} 24 Td <{_pdf_s(meta['name'] + ' ' + meta['version'] + f'  —  {n} / {len(pages)}').encode('utf-16-be').hex()}> Tj ET"
        c = add(b"<< /Filter /FlateDecode", zlib.compress("\n".join(pg + [foot]).encode("latin-1")))
        kids.append(add(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PDF_W} {PDF_H}] /Resources << /Font << /F1 {f1} 0 R >> >> /Contents {c} 0 R >>"))
    objs[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>".encode()
    info = add(f"<< /Title <FEFF{_pdf_s(meta['name']).encode('utf-16-be').hex()}> /Producer (build_docset.py) >>")
    out, offs = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"), []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode() + "".join(f"{o:010d} 00000 n \n" for o in offs).encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R /Info {info} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(bytes(out))


# HWPX: 한컴 OWPML(KS X 6101) zip. 표준 라이브러리(zipfile)로 최소 구성(header·section0·content.hpf)을 쓴다.
HWPX_BODY_W = 48190  # A4 폭 59528 − 좌우 여백 5669×2 (HWPUNIT)
_HNS = ('xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
        'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" '
        'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"')


def _hwpx_header():
    langs = ("HANGUL", "LATIN", "HANJA", "JAPANESE", "OTHER", "SYMBOL", "USER")
    faces = "".join(f'<hh:fontface lang="{l}" fontCnt="1"><hh:font id="0" face="{FONT}" type="TTF" isEmbedded="0"/></hh:fontface>' for l in langs)
    per = lambda tag, v: f'<hh:{tag} ' + " ".join(f'{l.lower()}="{v}"' for l in langs) + "/>"

    def border(i, line, fill=""):
        sides = "".join(f'<hh:{s}Border type="{line}" width="0.12 mm" color="#000000"/>' for s in ("left", "right", "top", "bottom"))
        return (f'<hh:borderFill id="{i}" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
                '<hh:slash type="NONE" Crooked="0" isCounter="0"/><hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
                f'{sides}<hh:diagonal type="SOLID" width="0.1 mm" color="#000000"/>{fill}</hh:borderFill>')

    def char(i, size, bold):
        return (f'<hh:charPr id="{i}" height="{size * 100}" textColor="#000000" shadeColor="none" useFontSpace="0" useKerning="0" '
                'symMark="NONE" borderFillIDRef="1">' + per("fontRef", 0) + per("ratio", 100) + per("spacing", 0) + per("relSz", 100) +
                per("offset", 0) + ("<hh:bold/>" if bold else "") + '<hh:underline type="NONE" shape="SOLID" color="#000000"/>'
                '<hh:strikeout shape="NONE" color="#000000"/><hh:outline type="NONE"/><hh:shadow type="NONE" color="#B2B2B2" offsetX="10" offsetY="10"/></hh:charPr>')

    def parap(i, align, spacing):
        return (f'<hh:paraPr id="{i}" tabPrIDRef="0" condense="0" fontLineHeight="0" snapToGrid="1" suppressLineNumbers="0" checked="0">'
                f'<hh:align horizontal="{align}" vertical="BASELINE"/><hh:heading type="NONE" idRef="0" level="0"/>'
                '<hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="BREAK_WORD" widowOrphan="0" keepWithNext="0" keepLines="0" '
                'pageBreakBefore="0" lineWrap="BREAK"/><hh:autoSpacing eAsianEng="0" eAsianNum="0"/>'
                '<hh:margin><hc:intent value="0" unit="HWPUNIT"/><hc:left value="0" unit="HWPUNIT"/><hc:right value="0" unit="HWPUNIT"/>'
                '<hc:prev value="0" unit="HWPUNIT"/><hc:next value="0" unit="HWPUNIT"/></hh:margin>'
                f'<hh:lineSpacing type="PERCENT" value="{spacing}" unit="HWPUNIT"/>'
                '<hh:border borderFillIDRef="1" offsetLeft="0" offsetRight="0" offsetTop="0" offsetBottom="0" connect="0" ignoreMargin="0"/></hh:paraPr>')

    head_fill = '<hc:fillBrush><hc:winBrush faceColor="#DCE6F1" hatchColor="#999999" alpha="0"/></hc:fillBrush>'
    chars = [char(0, 10, False), char(1, 16, True), char(2, 13, True), char(3, 11, True), char(4, 9, False), char(5, 9, True)]
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f'<hh:head {_HNS} version="1.4" secCnt="1"><hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1"/><hh:refList>'
            f'<hh:fontfaces itemCnt="7">{faces}</hh:fontfaces>'
            f'<hh:borderFills itemCnt="3">{border(1, "NONE")}{border(2, "SOLID")}{border(3, "SOLID", head_fill)}</hh:borderFills>'
            f'<hh:charProperties itemCnt="{len(chars)}">{"".join(chars)}</hh:charProperties>'
            '<hh:tabProperties itemCnt="1"><hh:tabPr id="0" autoTabLeft="0" autoTabRight="0"/></hh:tabProperties>'
            f'<hh:paraProperties itemCnt="3">{parap(0, "JUSTIFY", 160)}{parap(1, "CENTER", 160)}{parap(2, "LEFT", 130)}</hh:paraProperties>'
            '<hh:styles itemCnt="1"><hh:style id="0" type="PARA" name="바탕글" engName="Normal" paraPrIDRef="0" charPrIDRef="0" '
            'nextStyleIDRef="0" langID="1042" lockForm="0"/></hh:styles></hh:refList>'
            '<hh:compatibleDocument targetProgram="HWP201X"><hh:layoutCompatibility/></hh:compatibleDocument></hh:head>')


def render_hwpx(path, meta, blocks):
    seq = iter(range(1, 10 ** 7))
    plain = []

    def p(text, cp=0, pp=0, inner=None):
        if inner is None:
            plain.append(text)
        run = inner if inner is not None else f"<hp:t>{escape(text)}</hp:t>"
        return (f'<hp:p id="{next(seq)}" paraPrIDRef="{pp}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
                f'<hp:run charPrIDRef="{cp}">{run}</hp:run></hp:p>')

    def table(rows, head):
        n = max(len(r) for r in rows)
        rows = [[str(v) for v in r] + [""] * (n - len(r)) for r in rows]
        want = [max(min(max(len(r[j]) for r in rows), 40), 3) for j in range(n)]
        cw = [HWPX_BODY_W * w // sum(want) for w in want]
        cw[-1] += HWPX_BODY_W - sum(cw)
        trs = ""
        for i, r in enumerate(rows):
            hd = head and i == 0
            tcs = ""
            for j, v in enumerate(r):
                body = "".join(p(line, 5 if hd else 4, 2) for line in v.split("\n"))
                tcs += (f'<hp:tc name="" header="{int(hd)}" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="{3 if hd else 2}">'
                        '<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" '
                        f'textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">{body}</hp:subList>'
                        f'<hp:cellAddr colAddr="{j}" rowAddr="{i}"/><hp:cellSpan colSpan="1" rowSpan="1"/>'
                        f'<hp:cellSz width="{cw[j]}" height="1200"/><hp:cellMargin left="283" right="283" top="141" bottom="141"/></hp:tc>')
            trs += f"<hp:tr>{tcs}</hp:tr>"
        tbl = (f'<hp:tbl id="{next(seq)}" zOrder="0" numberingType="TABLE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
               f'dropcapstyle="None" pageBreak="CELL" repeatHeader="{int(head)}" rowCnt="{len(rows)}" colCnt="{n}" cellSpacing="0" '
               f'borderFillIDRef="2" noAdjust="0"><hp:sz width="{HWPX_BODY_W}" widthRelTo="ABSOLUTE" height="{1200 * len(rows)}" '
               'heightRelTo="ABSOLUTE" protect="0"/><hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
               'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
               '<hp:outMargin left="0" right="0" top="0" bottom="283"/><hp:inMargin left="283" right="283" top="141" bottom="141"/>'
               f"{trs}</hp:tbl>")
        return p("", inner=tbl + "<hp:t/>")

    sec_pr = ('<hp:secPr id="" textDirection="HORIZONTAL" spaceColumns="1134" tabStop="8000" tabStopVal="4000" tabStopUnit="HWPUNIT" '
              'outlineShapeIDRef="0" memoShapeIDRef="0" textVerticalWidthHead="0" masterPageCnt="0">'
              '<hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0"/><hp:startNum pageStartsOn="BOTH" page="0" pic="0" tbl="0" equation="0"/>'
              '<hp:visibility hideFirstHeader="0" hideFirstFooter="0" hideFirstMasterPage="0" border="SHOW_ALL" fill="SHOW_ALL" '
              'hideFirstPageNum="0" hideFirstEmptyLine="0" showLineNumber="0"/><hp:lineNumberShape restartType="0" countBy="0" distance="0" startNumber="0"/>'
              '<hp:pagePr landscape="WIDELY" width="59528" height="84186" gutterType="LEFT_ONLY">'
              '<hp:margin header="4252" footer="4252" gutter="0" left="5669" right="5669" top="5669" bottom="4252"/></hp:pagePr>'
              '<hp:pageBorderFill type="BOTH" borderFillIDRef="1" textBorder="PAPER" headerInside="0" footerInside="0" fillArea="PAPER">'
              '<hp:offset left="1417" right="1417" top="1417" bottom="1417"/></hp:pageBorderFill></hp:secPr>'
              '<hp:ctrl><hp:colPr id="" type="NEWSPAPER" layout="LEFT" colCount="1" sameSz="1" sameGap="0"/></hp:ctrl>')
    paras = [p("", inner=sec_pr)]
    for b in full_blocks(meta, blocks):
        if b[0] == "title":
            paras += [p(line, 1, 1) for line in b[1].split("\n")]
        elif b[0] in ("h1", "h2"):
            paras.append(p(b[1], 2 if b[0] == "h1" else 3))
        elif b[0] == "p":
            paras.append(p(b[1]))
        else:
            plain.extend(" | ".join(str(v) for v in r) for r in b[1])
            paras.append(table(b[1], b[2]))
    section = ('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
               f'<hs:sec {_HNS}>' + "".join(paras) + "</hs:sec>")
    hpf = ('<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
           f'<opf:package {_HNS} xmlns:opf="http://www.idpf.org/2007/opf/" version="" unique-identifier="" id="">'
           f'<opf:metadata><opf:title>{escape(meta["name"])}</opf:title><opf:language>ko</opf:language></opf:metadata>'
           '<opf:manifest><opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>'
           '<opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/>'
           '<opf:item id="settings" href="settings.xml" media-type="application/xml"/></opf:manifest>'
           '<opf:spine><opf:itemref idref="header" linear="yes"/><opf:itemref idref="section0" linear="yes"/></opf:spine></opf:package>')
    files = {
        "version.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?><hv:HCFVersion xmlns:hv="http://www.hancom.co.kr/hwpml/2011/version" '
                       'tagetApplication="WORDPROCESSOR" major="5" minor="1" micro="0" buildNumber="1" os="1" xmlVersion="1.4" '
                       'application="Hancom Office Hangul" appVersion="11, 0, 0, 0"/>',
        "META-INF/container.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?><ocf:container xmlns:ocf="urn:oasis:names:tc:opendocument:xmlns:container" '
                                  'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf"><ocf:rootfiles>'
                                  '<ocf:rootfile full-path="Contents/content.hpf" media-type="application/hwpml-package+xml"/>'
                                  '<ocf:rootfile full-path="Preview/PrvText.txt" media-type="text/plain"/></ocf:rootfiles></ocf:container>',
        "META-INF/manifest.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?><odf:manifest xmlns:odf="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"/>',
        "Contents/content.hpf": hpf,
        "Contents/header.xml": _hwpx_header(),
        "Contents/section0.xml": section,
        "settings.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?><ha:HWPApplicationSetting xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" '
                        'xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0"><ha:CaretPosition listIDRef="0" paraIDRef="0" pos="0"/></ha:HWPApplicationSetting>',
        "Preview/PrvText.txt": "\r\n".join(plain)[:1024],
    }
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/hwp+zip", compress_type=zipfile.ZIP_STORED)
        for name, data in files.items():
            z.writestr(name, data.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)


RENDER = {"xlsx": render_xlsx, "docx": render_docx, "pptx": render_pptx, "md": render_md,
          "pdf": render_pdf, "hwpx": render_hwpx, "txt": render_txt}

# ─────────────────────────── 비교·검출 ───────────────────────────


def cells(kind, body):
    """모델 → {위치 키 튜플: 값}. 마지막 원소는 항목(열) 이름."""
    out = {}
    if kind == "xlsx":
        for title, _, header, rows, _, keyc in body:
            for r in rows:
                k = (title,) + tuple(str(r[i]) for i in keyc)
                for i, h in enumerate(header):
                    if i not in keyc:
                        out[k + (h,)] = str(r[i])
    elif kind == "docx":
        h, ctx, n = "", "", 0
        for b in body:
            if b[0] in ("h1", "h2"):
                h, ctx, n = b[1], "", 0
            elif b[0] == "p":
                n += 1
                if len(b[1]) <= 20:
                    ctx = b[1]
                else:
                    out[(h, f"문단{n}", "본문")] = b[1]
            else:
                rows, head = b[1], b[2]
                if head:
                    for r in rows[1:]:
                        for i in range(1, len(r)):
                            out[(h, ctx, str(r[0]), rows[0][i])] = str(r[i])
                else:
                    for r in rows:
                        for i in range(0, len(r) - 1, 2):
                            if r[i]:
                                out[(h, ctx, str(r[i]), "값")] = str(r[i + 1])
    elif kind == "pptx":
        for sc in body["screens"]:
            for lbl, v in (("화면명", sc[1]), ("경로", sc[2]), ("사용자", sc[3]), ("관련 요구사항", ", ".join(sc[4])),
                           ("관련 인터페이스", ", ".join(sc[5])), ("담당 개발팀", body["team"][sc[7]])):
                out[(sc[0], "화면 정보", lbl)] = v
            for lb, ds in sc[6]:
                out[(sc[0], lb, "설명")] = ds
    else:
        for line in body.splitlines():
            if line.strip():
                out[("본문", line, "줄")] = line  # 값이 있어야 줄 추가·삭제가 diff에 잡힌다
    return out


def diff(kind, a, b):
    ca, cb = cells(kind, a), cells(kind, b)
    out = []
    for k in list(ca) + [k for k in cb if k not in ca]:
        x, y = ca.get(k), cb.get(k)
        if (x or "") != (y or ""):
            out.append(("추가" if x is None else "삭제" if y is None else "수정", " > ".join(p for p in k[:-1] if p), k[-1], x or "", y or ""))
    return out


def row_texts(kind, body):
    """행 단위 (위치, 텍스트) — 반복값 정규식 검사용."""
    rows = {}
    for k, v in cells(kind, body).items():
        rows.setdefault(k[:-1], []).append(v)
    return [(" > ".join(p for p in k if p), " ".join(k) + " " + " ".join(v)) for k, v in rows.items()]


def scan(P, models):
    """{항목: {값: [(문서키, 버전, 위치)]}}"""
    found = {}
    for wname, rx in P.WATCH:
        for k, (ver, kind, body, *_rest) in models.items():
            for loc, txt in row_texts(kind, body):
                for m in re.finditer(rx, txt):
                    val = "/".join(g for g in m.groups() if g)
                    hits = found.setdefault(wname, {}).setdefault(val, [])
                    if (k, ver, loc) not in hits:
                        hits.append((k, ver, loc))
    return found




# ─────────────────────────── 버전 엔진 ───────────────────────────


def apply_ops(d, ops):
    def rep(x, old, new):
        if isinstance(x, str):
            return x.replace(old, new), x.count(old)
        if isinstance(x, (list, tuple)):
            parts = [rep(y, old, new) for y in x]
            return type(x)(p[0] for p in parts), sum(p[1] for p in parts)
        return x, 0

    def find(key, iid):  # 항목 ID는 0번 열 값, (열, 값) 튜플이면 그 열로 찾는다(공통코드처럼 0번 열이 겹칠 때)
        col, val = iid if isinstance(iid, tuple) else (0, iid)
        return next(n for n, x in enumerate(d[key]) if x[col] == val)

    for op in ops:
        if op[0] == "rep":  # iid None = 그 데이터 전체(블록 문서 등)에서 치환
            _, key, iid, old, new = op
            if iid is None:
                d[key], cnt = rep(d[key], old, new)
            else:
                i = find(key, iid)
                d[key][i], cnt = rep(d[key][i], old, new)
            assert cnt, f"치환 대상 없음: {iid} '{old}'"
        elif op[0] == "set":  # ("set", 데이터, 항목 ID, 열 인덱스, 값)
            _, key, iid, col, val = op
            i = find(key, iid)
            d[key][i] = d[key][i][:col] + (val,) + d[key][i][col + 1:]
        elif op[0] == "add":  # ("add", 데이터, 행)
            d[op[1]].append(op[2])
        elif op[0] == "del":  # ("del", 데이터, 항목 ID) — 행 삭제
            del d[op[1]][find(op[1], op[2])]
        elif op[0] == "push":  # ("push", 데이터, 항목 ID, 열 인덱스, 값) — 항목 안 목록(화면 요소, 응답 항목 등)에 추가
            _, key, iid, col, val = op
            i = find(key, iid)
            d[key][i] = d[key][i][:col] + (list(d[key][i][col]) + [val],) + d[key][i][col + 1:]
        elif op[0] == "pull":  # ("pull", 데이터, 항목 ID, 열 인덱스, 이름) — 항목 안 목록에서 이름이 같은 요소 삭제
            _, key, iid, col, name = op
            i = find(key, iid)
            kept = [v for v in d[key][i][col] if v[0] != name]
            assert len(kept) < len(d[key][i][col]), f"삭제 대상 없음: {iid} '{name}'"
            d[key][i] = d[key][i][:col] + (kept,) + d[key][i][col + 1:]
        else:
            next(t for t in d["TB"] if t[0] == op[1])[3].append(op[2])


def fname(s, kind):
    return f"{s['no']:02d}_{s['name']}.{s.get('fmt', kind)}"


def meta_of(P, s, version, state, history, apv):
    return dict(name=s["name"], project=P.PROJECT, client=P.CLIENT, team=team_name(P)[s["team"]], version=version, state=state,
                grade=s["grade"], date=s["date"], author=pname(s["author"]), reviewer=pname(s["reviewer"]),
                approver=pname(apv), history=history, xl=s.get("xl"))


def build_project(P):
    out = DOC_DIR / P.FOLDER
    out.mkdir(parents=True, exist_ok=True)
    for p in out.iterdir():  # 폴더 자체는 남긴다(탐색기·터미널이 열고 있으면 Windows에서 삭제 실패)
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    d = {k: copy.deepcopy(getattr(P, k)) for k in P.DATA_KEYS}
    heads, hist = {}, {}
    for k, s in P.DOCS.items():
        kind, body = MODELS[s["model"]](P, d, s)
        apv = approver_of(P, s["team"], s["author"])
        hist[k] = [("v1", s["date"], "최초 작성", pname(s["author"]), pname(apv))]
        path = out / "v1" / fname(s, kind)
        path.parent.mkdir(parents=True, exist_ok=True)
        RENDER[s.get("fmt", kind)](path, meta_of(P, s, "v1", "HEAD 승인본", hist[k], apv), body)
        heads[k] = (1, kind, body, path, s["date"], apv)
    log, diffs = [], []
    for c in P.CHANGES:
        k, s = c["doc"], P.DOCS[c["doc"]]
        nd = copy.deepcopy(d)
        apply_ops(nd, c["ops"])
        kind, body = MODELS[s["model"]](P, nd, s)
        ver = heads[k][0] + 1
        dl = diff(kind, heads[k][2], body)
        assert dl, f"{c['id']} 변경 내용 없음"
        apv = approver_of(P, s["team"], c["author"], c.get("approver"))
        h = (f"v{ver}", c["done"] or c["req"], c["summary"], pname(c["author"]), pname(apv))
        if c["status"] == "승인":
            d = nd
            hist[k] = hist[k] + [h]
            path = out / f"v{ver}" / fname(s, kind)
            state = "HEAD 승인본"
        else:
            path = out / c["status"].replace(" ", "") / f"{c['id']}_{fname(s, kind)}"
            state = f"제출본({c['status']})"
        path.parent.mkdir(parents=True, exist_ok=True)
        RENDER[s.get("fmt", kind)](path, meta_of(P, s, f"v{ver}", state, hist[k] + ([] if c["status"] == "승인" else [h]), apv), body)
        if c["status"] == "승인":
            heads[k] = (ver, kind, body, path, c["done"], apv)
        log.append((c, heads[k][0] if c["status"] != "승인" else ver - 1, ver, path, apv))
        diffs += [(c["id"], s["name"], *x) for x in dl]
    found_head = scan(P, heads)
    write_truth(P, out, heads, log, diffs, found_head)
    write_overview(P, out, heads, log, found_head)
    return heads, log, hist


# ─────────────────────────── 정답·개요 ───────────────────────────


def write_truth(P, out, heads, log, diffs, found_head):
    tn = team_name(P)
    wb = Workbook()
    wb.remove(wb.active)
    rel = lambda p: p.relative_to(out).as_posix()
    xl_sheet(wb, "HEAD 현황", f"{P.PROJECT} — 문서별 HEAD ({P.ASOF} 기준)",
             ["문서 키", "문서", "소유 팀", "공개 범위", "형식", "HEAD 버전", "HEAD 반영일", "HEAD 승인자", "파일"],
             [(k, s["name"], tn[s["team"]], s["grade"], heads[k][3].suffix[1:], f"v{heads[k][0]}", heads[k][4],
               f"{pname(heads[k][5])}({heads[k][5]})", rel(heads[k][3])) for k, s in P.DOCS.items()],
             (8, 26, 20, 12, 6, 9, 12, 14, 50))
    xl_sheet(wb, "변경 요청", "변경 요청 이력 (승인 건만 HEAD 반영, 본인 승인 금지)",
             ["변경 ID", "문서", "기준 버전", "요청 버전", "상태", "작성자", "승인 담당", "승인 구분", "요청일", "처리일", "변경 사유", "변경 요약", "반려 사유", "파일"],
             [(c["id"], P.DOCS[c["doc"]]["name"], f"v{bv}", f"v{nv}", c["status"], f"{pname(c['author'])}({c['author']})",
               f"{pname(apv)}({apv})", apv_kind(P, P.DOCS[c["doc"]]["team"], c["author"], apv) + (f" — {c['apv_note']}" if c.get("apv_note") else ""),
               c["req"], c["done"], c["reason"], c["summary"], c.get("reject", ""), rel(p)) for c, bv, nv, p, apv in log],
             (9, 22, 8, 8, 9, 14, 14, 26, 11, 11, 36, 44, 36, 50))
    wb.save(out / "문서이력.xlsx")

    wb = Workbook()
    ws = wb.active
    ws.title = "안내"
    for r in [["변경 이력 정답 — 이 폴더 문서(v2 이상·승인대기·반려)에 실제로 일어난 변경의 diff와 영향 라벨"], [],
              ["DATA-03 테스트셋은 사람이 직접 만든 시나리오만 쓰고, 라벨은 시나리오 작성자가 아닌 2명이 따로 붙인다(DATA-04)."],
              [f"이 파일의 변경 {len(log)}건과 영향 라벨은 LLM이 만든 것이라 라벨 가이드(DATA-02) 경계 사례 예시나 학습용(DATA-06, 사람 검수 후)으로만 쓴다."],
              [f"변경 {len(log)}건은 같은 폴더의 v2 이상·승인대기·반려 파일과 문서이력.xlsx에 대응한다. 파싱·diff 조정 때 정답으로 쓴다."],
              ["학습용 가상 변경은 3_변경시나리오/ 의 변경시나리오_라벨.xlsx에 따로 있다."], [],
              ["시트", "내용"], ["변경 상세(diff)", "변경마다 기준 버전 대비 바뀐 칸(이전 값 → 이후 값)"],
              ["영향 팀 라벨", "변경마다 팀별 영향 있음 / 영향 없음(소유 팀은 판정 없이 항상 알림)"],
              ["반복값 위치(HEAD)", "같은 값이 나오는 문서·위치 — 새 변경 시나리오를 만들 때 영향 범위 근거"]]:
        ws.append(r)
    ws["A1"].font = Font(name=FONT, bold=True, size=14)
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 70
    xl_sheet(wb, "변경 상세(diff)", "변경 상세 — 기준 버전 대비 셀 단위 차이",
             ["변경 ID", "문서", "구분", "위치", "항목", "이전 값", "이후 값"], diffs, (9, 22, 6, 50, 14, 50, 50))
    rows = []
    for c, *_ in log:
        owner = P.DOCS[c["doc"]]["team"]
        given = {t: (j, why) for t, j, why in P.IMPACT[c["id"]]}
        for code, name, *_r in teams(P):
            if code == owner:  # 소유 팀도 자기 다른 문서 후속 작업이 있을 수 있음
                j, why = given.get(code, ("", "변경 작성·승인"))
                j = f"소유 팀({j})" if j else "소유 팀"
            elif c["status"] != "승인":
                j, why = "영향 없음", f"{c['status']} — HEAD 미반영, 알림 대상 아님"
            elif P.DOCS[c["doc"]]["grade"] == "팀 내부":
                j, why = "영향 없음", "팀 내부 문서 — 알림은 소유 팀 안에서만, 다른 팀 판정 대상 아님"
            else:
                j, why = given.get(code, ("영향 없음", ""))
            notify = ("알림 없음(HEAD 미반영)" if c["status"] != "승인" else
                      "항상 알림(규칙, LLM 판정 대상 아님)" if code == owner else
                      "알림 없음(팀 내부 문서)" if P.DOCS[c["doc"]]["grade"] == "팀 내부" else "LLM 판정 결과에 따름")
            rows.append((c["id"], c["status"], name, j, notify, why))
    xl_sheet(wb, "영향 팀 라벨", "변경별 팀 영향 라벨 — LLM 작성 예시, 테스트셋 아님 (영향 있음 / 영향 없음 — 소유 팀은 항상 알림)", ["변경 ID", "상태", "팀", "판정", "알림", "근거"], rows, (9, 9, 20, 16, 28, 70))
    xl_sheet(wb, "반복값 위치(HEAD)", "현재 HEAD에서 반복값이 나오는 위치 — 변경 시나리오 후보",
             ["항목", "값", "문서", "버전", "위치"],
             [(w, v, P.DOCS[k]["name"], f"v{ver}", loc) for w, vals in found_head.items() for v, hits in vals.items() for k, ver, loc in hits],
             (18, 10, 26, 6, 70))
    wb.save(out / "변경이력_정답.xlsx")


def head_data(P):
    d = {k: copy.deepcopy(getattr(P, k)) for k in P.DATA_KEYS}
    for c in P.CHANGES:
        if c["status"] == "승인":
            apply_ops(d, c["ops"])
    return d


def train_docs(P, heads, hist):
    """시나리오마다 HEAD에 변경 1건만 적용한 제출본 파일 생성 → {시나리오 ID: (파일, 기준 버전, diff 목록)}. 시나리오끼리 독립."""
    out = SCN_DIR / f"{P.FOLDER}_시나리오문서"
    out.mkdir(parents=True, exist_ok=True)
    for f in out.iterdir():
        f.unlink()
    hd, res = head_data(P), {}
    for n, (doc, _kind, key, loc, before, after, why, _labels, *ops) in enumerate(TRAIN[P.CODE], 1):
        sid, s = f"TR-{P.CODE}-{n:03d}", P.DOCS[doc]
        nd = copy.deepcopy(hd)
        if ops:
            apply_ops(nd, ops[0])
        else:
            iid = loc if any(x[0] == loc for x in nd[key]) else None  # 블록 문서는 문서 전체에서 치환
            apply_ops(nd, [("rep", key, iid, before, after)])
        kind, body = MODELS[s["model"]](P, nd, s)
        dl = diff(kind, heads[doc][2], body)
        assert dl, f"{sid} 문서에 변경이 안 생김"
        ver, apv = heads[doc][0], approver_of(P, s["team"], s["author"])
        path = out / f"{sid}_{fname(s, kind)}"
        h = (f"v{ver + 1}", P.ASOF, why, pname(s["author"]), pname(apv))
        RENDER[s.get("fmt", kind)](path, meta_of(P, s, f"v{ver + 1}", "제출본(학습용 시나리오)", hist[doc] + [h], apv), body)
        res[sid] = (path, ver, dl)
    return res


def train_rows(P, docs):
    """학습용 시나리오 → (시나리오 행, 라벨 행, diff 행). 소유 팀은 판정 대상이 아니라 쌍에서 뺀다."""
    tn = team_name(P)
    scn, lab, dif = [], [], []
    for n, (doc, kind, _key, loc, before, after, why, labels, *_ops) in enumerate(TRAIN[P.CODE], 1):
        sid, owner = f"TR-{P.CODE}-{n:03d}", P.DOCS[doc]["team"]
        path, ver, dl = docs[sid]
        given = {t: (f"영향 {j}", r) for t, j, r in labels}
        hit = 0
        for code, name, *_ in teams(P):
            if code == owner:
                continue
            j, r = given.get(code, ("영향 없음", ""))
            hit += j == "영향 있음"
            lab.append((sid, P.DOCS[doc]["name"], tn[owner], name, j, "Y" if r.startswith("경계") else "", r, "", ""))
        scn.append((sid, P.DOCS[doc]["name"], tn[owner], kind, loc, before or "(없음)", after or "(삭제)", why, hit,
                    f"v{ver}", path.relative_to(SCN_DIR).as_posix()))
        dif += [(sid, P.DOCS[doc]["name"], *x) for x in dl]
    return scn, lab, dif


def write_train(P, heads, hist):
    scn, lab, dif = train_rows(P, train_docs(P, heads, hist))
    wb = Workbook()
    ws = wb.active
    ws.title = "안내"
    rules = [ln.strip() for ln in TRAIN_DOC[P.CODE].split("라벨 기준")[1].splitlines()[1:] if ln.strip()]
    for r in [["변경 시나리오와 정답(diff·영향 라벨) — 학습·조정용, LLM 초안, 사람 검수 전 (DATA-06)"], [],
              ["테스트셋(DATA-03)이 아니다. 검수자가 '검수 결과' 칸에 확인·수정을 적은 뒤 학습·프롬프트 조정에 쓴다."],
              [f"시나리오마다 현재 HEAD를 기준으로 서로 독립인 가상 제출 1건이다. 제출본 파일은 {P.FOLDER}_시나리오문서/ 에 있다."],
              ["유형 '여러 곳 변경'은 서로 관계없는 변경 여러 개를 한 번에 제출한 경우다(위치·이전·이후는 ①②로 나눠 적음). 영향 라벨은 모든 변경을 합친 기준이다."],
              ["시험 방법: 1_문서세트의 HEAD를 올린 뒤, 시나리오 파일을 '기준 버전' 열의 버전을 고친 제출본으로 넣는다. 승인하지 말고 다음 시나리오로 넘어간다."],
              ["채점: 파이프라인 diff ↔ '변경 상세(diff)' 시트, 영향 판정 ↔ '영향 라벨' 시트."],
              ["소유 팀은 항상 알림이라 판정 쌍에서 뺐다. '경계'가 Y인 쌍은 라벨 가이드(DATA-02) 경계 사례 후보다."], [],
              ["라벨 기준"]] + [[x] for x in rules]:
        ws.append(r)
    ws["A1"].font = Font(name=FONT, bold=True, size=14)
    ws.column_dimensions["A"].width = 120
    xl_sheet(wb, "시나리오", f"{P.PROJECT} — 변경 시나리오 {len(scn)}건 (HEAD 기준, 서로 독립)",
             ["시나리오 ID", "문서", "소유 팀", "유형", "위치", "이전", "이후", "변경 사유", "영향 있음 팀 수", "기준 버전", "제출본 파일"], scn,
             (11, 22, 18, 9, 14, 40, 40, 30, 8, 8, 50))
    xl_sheet(wb, "변경 상세(diff)", "변경 상세 — 기준 버전(HEAD) 대비 셀 단위 차이 (파이프라인 diff 정답)",
             ["시나리오 ID", "문서", "구분", "위치", "항목", "이전 값", "이후 값"], dif, (11, 22, 6, 50, 14, 50, 50))
    xl_sheet(wb, "영향 라벨", "변경 × 팀 영향 라벨 (소유 팀 제외) — LLM 초안, 검수 전",
             ["시나리오 ID", "문서", "소유 팀", "팀", "판정", "경계", "근거", "검수자", "검수 결과"], lab,
             (11, 22, 18, 20, 10, 5, 70, 8, 20))
    pos = sum(r[4] == "영향 있음" for r in lab)
    kinds = sorted({r[3] for r in scn})
    owners = sorted({r[2] for r in scn})
    xl_sheet(wb, "분포", "라벨·유형 분포", ["구분", "값", "건수"],
             [("쌍", "전체", len(lab)), ("쌍", "영향 있음", pos), ("쌍", "영향 없음", len(lab) - pos),
              ("쌍", "영향 있음 비율", f"{pos / len(lab):.1%}"), ("쌍", "경계 사례", sum(r[5] == "Y" for r in lab)),
              ("시나리오", "전체", len(scn)), ("시나리오", "전 팀 영향 없음", sum(r[8] == 0 for r in scn))] +
             [("유형", k, sum(r[3] == k for r in scn)) for k in kinds] +
             [("소유 팀", o, sum(r[2] == o for r in scn)) for o in owners], (10, 22, 8))
    wb.save(SCN_DIR / f"{P.FOLDER}_변경시나리오_라벨.xlsx")
    return len(scn), len(lab), pos, len(dif)


def write_overview(P, out, heads, log, found_head):
    tn, ro = team_name(P), roster(P)
    L = [f"# {P.CODE}. {P.PROJECT} — 프로젝트 개요·팀 구성 (가상)", "",
         f"> DATA-01 가상 프로젝트 문서 세트(데이터셋 개정 {P.FOLDER[:8]}). 실존 회사·인물과 무관한 가상 데이터입니다.",
         "> 폴더명의 날짜는 데이터셋 개정일, 안쪽 v1·v2·v3는 문서 버전입니다.",
         "> 시스템(HEAD·검색·챗봇)에 올리는 것은 v1·v2… 버전 폴더의 문서뿐입니다. 승인대기·반려는 제출본, `문서이력.xlsx`는 이력 기록이며,",
         f"> 이 폴더 변경의 정답(diff·영향 라벨)은 `변경이력_정답.xlsx`, 질문셋은 `2_질문셋/`, 학습용 변경 시나리오는 `3_변경시나리오/`에 있습니다.", "",
         "## 1. 프로젝트", "", "| 항목 | 내용 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in P.OVERVIEW] + [
         f"| 수행사 | {company.COMPANY} |", "",
         "## 2. 조직과 역할", "",
         f"- 오너(PM): {pname(P.OWNER)}({P.OWNER}) — 프로젝트 생성·종료, PMO 문서 승인",
         f"- PMO 멤버: " + ", ".join(f"{pname(m)}({m})" for m in P.PMO[3]),
         ("- 승인자 = 소유 팀 팀장. 팀장이 작성한 문서는 같은 팀 대리 승인자가 승인하고(본인 승인 금지), 팀장 부재 시에도 대리 승인자가 승인한다"
          if deputy(P) else "- 작성자 = 멤버, 승인자 = 소유 팀 팀장 (본인 승인 없음)")]
    others = [Q for Q in PROJECTS if Q is not P]
    dual = [(pid, role, [f"{Q.CODE}:{roster(Q)[pid][1]}" for Q in others if pid in roster(Q)]) for pid, role in roster(P).items()]
    dual = [(pid, role, o) for pid, role, o in dual if o]
    if dual:
        L.append("- 다른 프로젝트 동시 수행: " + ", ".join(f"{pname(pid)}({pid}, {P.CODE}:{role[1]} · {', '.join(o)})" for pid, role, o in dual))
    dp = deputy(P)
    L += ["", "| 팀 | 팀장 | " + ("대리 승인자 | " if dp else "") + "멤버 | 하는 일 | 소유 문서 | 주로 참조하는 문서 |",
          "|---|---|" + ("---|" if dp else "") + "---|---|---|---|"]
    for code, name, ldr, members, job in P.TEAMS:
        own = ", ".join(s["name"] for s in P.DOCS.values() if s["team"] == code)
        refs = ", ".join(P.DOCS[r]["name"] for r in P.REFS[code])
        L.append(f"| {name} | {pname(ldr)}({ldr}) | " + (f"{pname(dp[code])}({dp[code]}) | " if dp else "") +
                 ", ".join(f"{pname(m)}({m})" for m in members) + f" | {job} | {own} | {refs} |")
    L += ["", "게스트(발주처, 오너가 프로젝트 단위로 초대 — '외부 공유' 문서만 열람, MCP 불가):", ""] + [f"- {x[1]}({x[0]}) — {x[4]} {x[3]}, {x[2]}" for x in P.EXTERNAL]
    L += ["", "## 3. 문서 공개 범위 4단계", "", "> 261118 기획서 최종본 4-1 기준. 오너(PM)는 모든 문서를 볼 수 있습니다.", "",
          "| 공개 범위 | 열람 가능 |", "|---|---|"] + [f"| {g} | {w} |" for g, w in P.GRADES]
    L += ["", f"## 4. 문서 목록과 HEAD ({P.ASOF} 기준)", "",
          "| No | 문서 | 형식 | 소유 팀 | 작성자 | HEAD 승인자 | 공개 범위 | HEAD | HEAD 파일 |", "|---|---|---|---|---|---|---|---|---|"]
    for k, s in P.DOCS.items():
        L.append(f"| {s['no']:02d} | {s['name']} | {heads[k][3].suffix[1:]} | {tn[s['team']]} | {pname(s['author'])} | {pname(heads[k][5])} | {s['grade']} | "
                 f"v{heads[k][0]} | `{heads[k][3].relative_to(out).as_posix()}` |")
    top = max(h[0] for h in heads.values())
    L += ["", "## 5. ID 체계와 참조 방향", ""] + P.ID_NOTES + [
          "- 요구사항정의서 '6. 요구사항 추적표'가 이 연결을 한 표로 보여 준다. `build_docset.py`의 `check()`가 참조가 끊기지 않았는지 검사한다.", "",
          "## 6. 폴더 구조", "", "```",
          f"{P.FOLDER}/", "  00_프로젝트개요_팀구성.md   이 파일", f"  v1/        기준선 — {len(P.DOCS)}개 문서 모두 v1",
          f"  v2/ ~ v{top}/   승인된 변경으로 생긴 그 버전의 문서만 (문서별 HEAD = 가장 높은 버전 폴더)",
          "  승인대기/  승인 담당자가 아직 처리하지 않은 제출본 (HEAD 아님, 승인 화면 비교용)",
          "  반려/      반려된 제출본 (HEAD 아님, 반려 사유는 문서이력.xlsx의 '변경 요청' 시트)",
          "  문서이력.xlsx  문서별 HEAD 현황 + 변경 요청 이력(승인·반려·대기)",
          "  변경이력_정답.xlsx  위 변경들의 diff 정답·영향 팀 라벨·반복값 위치", "```", "",
          "## 7. 변경 요청 요약", "", "| 변경 ID | 문서 | 버전 | 상태 | 작성자 → 승인 담당 | 승인 구분 | 처리일 | 요약 |", "|---|---|---|---|---|---|---|---|"]
    for c, bv, nv, _, apv in log:
        s = P.DOCS[c["doc"]]
        L.append(f"| {c['id']} | {s['name']} | v{bv} → v{nv} | {c['status']} | {pname(c['author'])} → {pname(apv)} | "
                 f"{apv_kind(P, s['team'], c['author'], apv)} | {c['done'] or '-'} | {c['summary']} |")
    L += ["", "## 8. 반복되는 값 (현재 HEAD, 정규식 자동 검출)", "",
          "⚠️는 문서마다 값이 다르다는 뜻입니다(변경이 일부 문서에만 반영된 상태 등). 위치 전체는 `변경이력_정답.xlsx`의 '반복값 위치(HEAD)' 시트에 있습니다.", "",
          "| 항목 | 값 | 나오는 문서 |", "|---|---|---|"]
    for w, vals in found_head.items():
        for v, hits in vals.items():
            docs = sorted({(P.DOCS[k]["no"], P.DOCS[k]["name"]) for k, *_ in hits})
            L.append(f"| {w}{' ⚠️' if len(vals) > 1 else ''} | {v} | {', '.join(n for _, n in docs)} |")
    (out / "00_프로젝트개요_팀구성.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def write_company():
    wb = Workbook()
    wb.remove(wb.active)
    assign = {}
    rows2 = []
    for P in PROJECTS:
        tn = team_name(P)
        for pid, (code, role) in roster(P).items():
            assign.setdefault(pid, []).append(f"{P.CODE}:{role}")
            rows2.append((P.CODE, P.PROJECT, pid, pname(pid), tn.get(code, "-"), role))
    xl_sheet(wb, "직원 명단", f"{company.COMPANY} 직원 명단 (가상)", ["사번", "이름", "직급", "직무", "소속 본부", "이메일", "배치(프로젝트:역할)"],
             [(e[0], e[1], e[2], e[3], e[4], f"{e[0].lower()}@{company.MAIL_DOMAIN}", ", ".join(assign.get(e[0], [])) or "미배치") for e in company.EMPLOYEES],
             (7, 8, 6, 22, 18, 24, 18))
    xl_sheet(wb, "프로젝트 배치", "프로젝트별 배치와 역할 (같은 사람이 프로젝트마다 다른 역할 가능)", ["프로젝트", "프로젝트명", "사번", "이름", "팀", "역할"],
             sorted(rows2), (8, 28, 7, 8, 22, 8))
    xl_sheet(wb, "외부 인원", "발주처 등 외부 인원", ["ID", "이름", "직급", "업무", "소속"], [x for P in PROJECTS for x in P.EXTERNAL], (6, 8, 6, 24, 12))
    wb.save(DOC_DIR / "회사_인원풀.xlsx")


def write_questions(P):
    """프로젝트별 질문셋. '미지정'(프로젝트가 애매한 질문)은 모든 프로젝트 파일에 넣고, 질문자 정보는 그 프로젝트 배치로 푼다."""
    qs = [q for q in questions.QUESTIONS if q[0] in (P.CODE, "미지정")]
    wb = Workbook()
    wb.remove(wb.active)
    rows = []
    for n, (pc, q, intent, kind, asker, refs, note) in enumerate(qs, 1):
        code, role = roster(P).get(asker, ("-", "프로젝트 밖 사내 구성원"))
        team = team_name(P).get(code) or ("발주처" if role == "게스트" else "소속 팀 없음")
        rows.append((f"Q{n:03d}", pc, q, intent, kind, asker, f"{pname(asker)} · {team} · {role}", refs, note))
    xl_sheet(wb, "질문", f"{P.PROJECT} — 사용자 질문 의도 평가셋 (DATA-07 초안, 데이터셋 개정 {P.FOLDER[:8]})",
             ["질문 ID", "프로젝트", "질문", "의도(정답, 복수는 ;)", "유형", "질문자 사번", "질문자(이름·팀·역할)", "관련 문서·ID", "정답·비고"],
             rows, (8, 8, 48, 22, 7, 9, 28, 24, 60))
    counts = {}
    for q in qs:
        for i in q[2].split(";"):
            counts[i] = counts.get(i, 0) + 1
    kinds = {k: sum(q[3] == k for q in qs) for k in ("단일", "애매", "복합", "범위 밖")}
    xl_sheet(wb, "분포", "라벨 분포", ["구분", "값", "건수"],
             [("의도", k, counts.get(k, 0)) for k in sorted(questions.INTENTS)] + [("유형", k, v) for k, v in kinds.items()] +
             [("전체", "질문 수", len(qs))], (8, 14, 8))
    Q_DIR.mkdir(exist_ok=True)
    wb.save(Q_DIR / f"{P.FOLDER}_질문셋.xlsx")


# ─────────────────────────── 검증 ───────────────────────────


def check(P):
    FR, SCR, IF, TB, TC, PROC = P.FR, P.SCR, P.IF, P.TB, P.TC, P.PROC
    fr, nfr, scr, ifs, tbs = {f[0] for f in FR}, {n[0] for n in P.NFR}, {s[0] for s in SCR}, {i[0] for i in IF}, {t[0] for t in TB}
    codes = {t[0] for t in teams(P)}
    for f in FR:
        assert f[10] in codes, f[0]
        for s in split_ids(f[9]):
            assert s in scr, (f[0], s)
            assert f[0] in next(x[4] for x in SCR if x[0] == s), f"{f[0]} -> {s} 역참조 없음"
    for s in SCR:
        assert set(s[4]) <= fr and set(s[5]) <= ifs and s[7] in codes, s[0]
    if_teams = {s["team"] for s in P.DOCS.values() if s["model"] == "if"}
    eif_team = next(s["team"] for s in P.DOCS.values() if s.get("eif"))
    for i in IF:
        assert set(i[8]) <= scr and set(i[9]) <= tbs and i[13] in if_teams, i[0]
        assert i[13] == eif_team or i[2] in ("내부 API", "배치"), f"{i[0]} 외부 연계는 연계정의서 소유 팀"
        for s in i[8]:
            assert i[0] in next(x[5] for x in SCR if x[0] == s), f"{i[0]} -> {s} 역참조 없음"
    for p in PROC:
        for st in p[4]:
            assert st[4] in fr and set(split_ids(st[5])) <= ifs, (p[0], st)
    for t in TC:
        assert set(split_ids(t[2])) <= fr | nfr and set(split_ids(t[3])) <= scr | ifs and t[7] in EMP, t[0]
    assert {p[0] for p in P.PERM} <= fr
    assert not {f for f in fr if not any(f in s[4] for s in SCR)}, "화면 없는 요구사항"
    assert not {t for t in tbs if not any(t in i[9] for i in IF)}, "인터페이스 없는 테이블"
    for t in TB:
        for c in t[3]:
            if "FK" in c[4]:
                rt, rc = re.match(r"(\w+)\.(\w+)", c[6]).groups()
                assert any(c2[0] == rc for x in TB if x[0] == rt for c2 in x[3]), (t[0], c[0])
    # 조직: 팀장 ≠ 멤버, 멤버 3명 이상, 대리 승인자는 같은 팀 멤버, 작성자는 소유 팀 소속, 승인자 ≠ 작성자(본인 승인 금지)
    ro, ld, dp = roster(P), lead(P), deputy(P)
    for code, _, ldr, members, _ in P.TEAMS:
        assert len(members) >= 3 and ldr not in members, code
    for code, x in dp.items():
        assert x in next(t[3] for t in teams(P) if t[0] == code), f"{code} 대리 승인자는 같은 팀 멤버"
    for k, s in P.DOCS.items():
        assert s["grade"] in {g[0] for g in P.GRADES}, f"{k} 공개 범위"
        assert in_team(P, s["author"], s["team"]) and approver_of(P, s["team"], s["author"]) != s["author"], f"{k} 작성자"
    dates = [c["req"] for c in P.CHANGES]
    assert dates == sorted(dates), "CHANGES는 요청일 순"
    for c in P.CHANGES:
        team = P.DOCS[c["doc"]]["team"]
        apv = approver_of(P, team, c["author"], c.get("approver"))
        assert in_team(P, c["author"], team), f"{c['id']} 작성자는 소유 팀 소속"
        assert apv != c["author"] and apv in (ld[team], dp.get(team)), f"{c['id']} 승인자는 작성자가 아닌 팀장·대리 승인자"
        assert c["id"] in P.IMPACT
    for q in (q for q in questions.QUESTIONS if q[0] in (P.CODE, "미지정")):
        assert set(q[2].split(";")) <= questions.INTENTS, f"의도 라벨 오타: {q[1]}"
        assert q[4] in ro or q[4] in EMP, f"질문자 없음: {q[1]}"
    # 학습용 시나리오: 이전 문자열이 HEAD 해당 항목에 실제로 있는지, 팀·판정 값이 맞는지
    hd = head_data(P)
    for n, (doc, kind, key, loc, before, after, why, labels, *ops) in enumerate(TRAIN.get(P.CODE, []), 1):
        sid = f"TR-{P.CODE}-{n:03d}"
        assert doc in P.DOCS and key in hd and kind in KINDS, sid
        assert kind != "여러 곳 변경" or (ops and len(ops[0]) >= 2), f"{sid}: 여러 곳 변경은 ops 2개 이상"
        if before and not ops:  # ops가 있으면 ops가 대상 존재를 검사한다(rep·pull assert)
            items = [x for x in hd[key] if x[0] == loc] or hd[key]  # 블록 문서(ARCH 등)는 문서 전체에서 찾는다
            assert any(before in str(x) for x in items), f"{sid}: HEAD {loc}에 '{before}' 없음"
        assert before or after, sid
        for t, j, r in labels:
            assert t in codes and t != P.DOCS[doc]["team"] and j in ("있음", "없음"), (sid, t)
            assert j == "없음" or r, f"{sid} {t}: 영향 있음은 근거 필수"
        assert len({t for t, *_ in labels}) == len(labels), f"{sid}: 팀 중복"


if __name__ == "__main__":
    import sys

    import diff_cases
    built = {}
    for P in PROJECTS:
        check(P)
        heads, log, hist = build_project(P)
        built[P.CODE] = (P, heads, hist)
        print(f"{P.FOLDER}: 문서 {len(P.DOCS)} · FR {len(P.FR)} · NFR {len(P.NFR)} · 프로세스 {len(P.PROC)} · SCR {len(P.SCR)} · IF {len(P.IF)} · "
              f"TB {len(P.TB)} · TC {len(P.TC)} · 변경 {len(log)} · HEAD " + ", ".join(f"{k}=v{v[0]}" for k, v in heads.items()))
        if P.CODE in TRAIN:
            print("학습용 시나리오 %d건 · 쌍 %d · 영향 있음 %d · diff %d칸" % write_train(P, heads, hist))
    write_company()
    for P in PROJECTS:
        write_questions(P)
    print(f"질문 {len(questions.QUESTIONS)} -> {ROOT}")
    print("diff 노이즈·경계 케이스 %d쌍" % diff_cases.build(sys.modules[__name__], built))
