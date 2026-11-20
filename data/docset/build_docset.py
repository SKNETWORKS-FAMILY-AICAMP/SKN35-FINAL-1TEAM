"""DATA-01 가상 SI 문서 세트 생성기 (데이터셋 개정 26.11.19).

데이터셋 개정판은 날짜로 부른다(폴더명 예: 26.11.19쇼핑몰A). v1·v2·v3는 문서 버전에만 쓴다.

  company.py       가상 SI사 인원 풀 (프로젝트 밖에서 관리 → B 프로젝트가 같은 사람 재사용)
  project_a.py     A 프로젝트(가나유통 온라인몰 차세대 구축) 데이터·변경 요청·정답
  questions.py     사용자 질문 의도 평가셋 (프로젝트 열 포함)
  build_docset.py  렌더러 + 버전 엔진 + 정답 생성 + 교차 검증 (이 파일)

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
from pathlib import Path

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
import questions

ROOT = Path(__file__).parent
DOC_DIR, Q_DIR, SCN_DIR = ROOT / "1_문서세트", ROOT / "2_질문셋", ROOT / "3_변경시나리오"  # DATA-01 / DATA-07 / DATA-03
FONT = "맑은 고딕"
PROJECTS = [project_a]
EMP = {e[0]: e for e in company.EMPLOYEES}
EXT = {x[0]: x for p in PROJECTS for x in p.EXTERNAL}
KIND_EXT = {"xlsx": "xlsx", "docx": "docx", "pptx": "pptx", "md": "md"}


def pname(pid):
    return (EMP.get(pid) or EXT[pid])[1]


def teams(P):
    return P.TEAMS + [P.PMO]


def team_name(P):
    return {t[0]: t[1] for t in teams(P)}


def lead(P):
    return {t[0]: t[2] for t in teams(P)}


def roster(P):
    """사번 → (팀 코드, 역할). 오너 > 팀장 > 멤버 > 게스트. 명단에 없는 사내 직원은 '프로젝트 밖'."""
    r = {}
    for code, _, ld, members, _ in teams(P):
        r[ld] = (code, "팀장")
        for m in members:
            r[m] = (code, "멤버")
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
        ("3. 권한 매트릭스", "3. 역할별 권한 매트릭스 (O 가능 · △ 조건부 · X 불가)", ["요구사항 ID", "기능", "비회원", "회원", "관리자", "조건·비고"],
         [(p[0], next(f[2] for f in FR if f[0] == p[0]), *p[1:]) for p in d["PERM"]], (11, 22, 8, 8, 8, 34), (0,)),
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
         ("p", "본 문서는 구 쇼핑몰의 현행(As-Is) 업무와 차세대 시스템의 개선(To-Be) 업무 흐름을 정의한다. 각 단계는 요구사항(FR)과 인터페이스(IF)에 연결되며, "
               "업무 규칙(BR)과 예외 흐름(EX)은 화면·인터페이스·테스트케이스 설계의 기준이 된다."),
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
        ("2. 퍼블리싱 목록", "2. 화면별 퍼블리싱 목록 (2026-11-18 기준)", ["화면 ID", "화면명", "퍼블리싱 파일", "담당", "상태", "완료(예정)일"],
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
    if s["team"] == "CT":
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
        ("1. 테이블 목록", "1. 테이블 목록 (DBMS: MySQL 8.0, 스키마: vsm)", ["No", "테이블명", "테이블 한글명", "설명", "담당 업무팀", "관련 인터페이스"],
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
        ("1. 테스트케이스", "1. 테스트케이스 및 수행 결과 (2026-11-18 기준)",
         ["TC ID", "단계", "관련 요구사항", "관련 화면·IF", "시나리오", "입력·조건", "기대 결과", "담당", "수행 결과", "수행일", "결함 ID"],
         [t[:7] + (pname(t[7]),) + t[8:] for t in d["TC"]], (8, 6, 12, 18, 22, 36, 40, 8, 9, 12, 9), (0,)),
        ("2. 결함 목록", "2. 결함 목록", ["결함 ID", "TC", "발견일", "심각도", "내용", "원인 구분", "조치 팀", "조치 상태"],
         d["DEFECTS"], (9, 8, 12, 7, 50, 44, 18, 18), (0,)),
        ("3. 수행 요약", "3. 단계별 수행 요약", ["단계", "수행 결과", "건수"],
         [(k, r, n) for k, v in summ.items() for r, n in sorted(v.items())], (10, 10, 8), (0, 1)),
    ]


def m_wbs(P, d, s):
    return "xlsx", [
        ("1. WBS", "1. WBS (2026-11-18 기준)", ["WBS ID", "단계", "작업", "담당 팀", "산출물", "시작", "종료", "진척률", "상태"], d["WBS"],
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
    for s in sheets:
        xl_sheet(wb, *s[:5])
    wb.save(path)


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


RENDER = {"xlsx": render_xlsx, "docx": render_docx, "pptx": render_pptx, "md": render_md}

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
                out[("본문", line, "")] = ""
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

    for op in ops:
        if op[0] == "rep":
            _, key, iid, old, new = op
            i = next(n for n, x in enumerate(d[key]) if x[0] == iid)
            d[key][i], cnt = rep(d[key][i], old, new)
            assert cnt, f"치환 대상 없음: {iid} '{old}'"
        else:
            next(t for t in d["TB"] if t[0] == op[1])[3].append(op[2])


def fname(s, kind):
    return f"{s['no']:02d}_{s['name']}.{KIND_EXT[kind]}"


def meta_of(P, s, version, state, history):
    return dict(name=s["name"], project=P.PROJECT, client=P.CLIENT, team=team_name(P)[s["team"]], version=version, state=state,
                grade=s["grade"], date=s["date"], author=pname(s["author"]), reviewer=pname(s["reviewer"]),
                approver=pname(lead(P)[s["team"]]), history=history)


def build_project(P):
    out = DOC_DIR / P.FOLDER
    if out.exists():
        shutil.rmtree(out)
    d = {k: copy.deepcopy(getattr(P, k)) for k in P.DATA_KEYS}
    ld = lead(P)
    heads, hist = {}, {}
    for k, s in P.DOCS.items():
        kind, body = MODELS[s["model"]](P, d, s)
        hist[k] = [("v1", s["date"], "최초 작성", pname(s["author"]), pname(ld[s["team"]]))]
        path = out / "v1" / fname(s, kind)
        path.parent.mkdir(parents=True, exist_ok=True)
        RENDER[kind](path, meta_of(P, s, "v1", "HEAD 승인본", hist[k]), body)
        heads[k] = (1, kind, body, path, s["date"])
    log, diffs = [], []
    for c in P.CHANGES:
        k, s = c["doc"], P.DOCS[c["doc"]]
        nd = copy.deepcopy(d)
        apply_ops(nd, c["ops"])
        kind, body = MODELS[s["model"]](P, nd, s)
        ver = heads[k][0] + 1
        dl = diff(kind, heads[k][2], body)
        assert dl, f"{c['id']} 변경 내용 없음"
        h = (f"v{ver}", c["done"] or c["req"], c["summary"], pname(c["author"]), pname(ld[s["team"]]))
        if c["status"] == "승인":
            d = nd
            hist[k] = hist[k] + [h]
            path = out / f"v{ver}" / fname(s, kind)
            state = "HEAD 승인본"
        else:
            path = out / c["status"].replace(" ", "") / f"{c['id']}_{fname(s, kind)}"
            state = f"제출본({c['status']})"
        path.parent.mkdir(parents=True, exist_ok=True)
        RENDER[kind](path, meta_of(P, s, f"v{ver}", state, hist[k] + ([] if c["status"] == "승인" else [h])), body)
        if c["status"] == "승인":
            heads[k] = (ver, kind, body, path, c["done"])
        log.append((c, heads[k][0] if c["status"] != "승인" else ver - 1, ver, path))
        diffs += [(c["id"], s["name"], *x) for x in dl]
    found_head = scan(P, heads)
    write_truth(P, out, heads, log, diffs, found_head)
    write_overview(P, out, heads, log, found_head)
    return heads, log


# ─────────────────────────── 정답·개요 ───────────────────────────


def write_truth(P, out, heads, log, diffs, found_head):
    tn, ld = team_name(P), lead(P)
    wb = Workbook()
    wb.remove(wb.active)
    rel = lambda p: p.relative_to(out).as_posix()
    xl_sheet(wb, "HEAD 현황", f"{P.PROJECT} — 문서별 HEAD (2026-11-18 기준)",
             ["문서 키", "문서", "소유 팀", "공개 범위", "HEAD 버전", "HEAD 반영일", "파일"],
             [(k, s["name"], tn[s["team"]], s["grade"], f"v{heads[k][0]}", heads[k][4], rel(heads[k][3])) for k, s in P.DOCS.items()],
             (8, 26, 20, 12, 9, 12, 50))
    xl_sheet(wb, "변경 요청", "변경 요청 이력 (승인 건만 HEAD 반영)",
             ["변경 ID", "문서", "기준 버전", "요청 버전", "상태", "작성자", "승인 담당", "요청일", "처리일", "변경 사유", "변경 요약", "반려 사유", "파일"],
             [(c["id"], P.DOCS[c["doc"]]["name"], f"v{bv}", f"v{nv}", c["status"], f"{pname(c['author'])}({c['author']})",
               f"{pname(ld[P.DOCS[c['doc']]['team']])}({ld[P.DOCS[c['doc']]['team']]})", c["req"], c["done"], c["reason"], c["summary"],
               c.get("reject", ""), rel(p)) for c, bv, nv, p in log], (9, 22, 8, 8, 9, 14, 14, 11, 11, 36, 44, 36, 50))
    wb.save(out / "문서이력.xlsx")

    wb = Workbook()
    ws = wb.active
    ws.title = "안내"
    for r in [["변경 예시와 영향 라벨 — LLM 작성 예시, 테스트셋 아님"], [],
              ["DATA-03 테스트셋은 사람이 직접 만든 시나리오만 쓰고, 라벨은 시나리오 작성자가 아닌 2명이 따로 붙인다(DATA-04)."],
              ["이 파일의 변경 10건과 영향 라벨은 LLM이 만든 것이라 라벨 가이드(DATA-02) 경계 사례 예시나 학습용(DATA-06, 사람 검수 후)으로만 쓴다."],
              ["변경 10건은 1_문서세트의 v2·v3·승인대기·반려 파일과 문서이력.xlsx에 대응한다."], [],
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
            else:
                j, why = given.get(code, ("영향 없음", ""))
            notify = ("알림 없음(HEAD 미반영)" if c["status"] != "승인" else
                      "항상 알림(규칙, LLM 판정 대상 아님)" if code == owner else "LLM 판정 결과에 따름")
            rows.append((c["id"], c["status"], name, j, notify, why))
    xl_sheet(wb, "영향 팀 라벨", "변경별 팀 영향 라벨 — LLM 작성 예시, 테스트셋 아님 (영향 있음 / 영향 없음 — 소유 팀은 항상 알림)", ["변경 ID", "상태", "팀", "판정", "알림", "근거"], rows, (9, 9, 20, 16, 28, 70))
    xl_sheet(wb, "반복값 위치(HEAD)", "현재 HEAD에서 반복값이 나오는 위치 — 변경 시나리오 후보",
             ["항목", "값", "문서", "버전", "위치"],
             [(w, v, P.DOCS[k]["name"], f"v{ver}", loc) for w, vals in found_head.items() for v, hits in vals.items() for k, ver, loc in hits],
             (18, 10, 26, 6, 70))
    SCN_DIR.mkdir(exist_ok=True)
    wb.save(SCN_DIR / f"{P.FOLDER}_변경예시_영향라벨.xlsx")


def write_overview(P, out, heads, log, found_head):
    tn, ro = team_name(P), roster(P)
    L = [f"# {P.CODE}. {P.PROJECT} — 프로젝트 개요·팀 구성 (가상)", "",
         f"> DATA-01 가상 프로젝트 문서 세트(데이터셋 개정 {P.FOLDER[:8]}). 실존 회사·인물과 무관한 가상 데이터입니다.",
         "> 폴더명의 날짜는 데이터셋 개정일, 안쪽 v1·v2·v3는 문서 버전입니다.",
         "> 시스템(HEAD·검색·챗봇)에 올리는 것은 v1·v2·v3 문서뿐입니다. 승인대기·반려는 제출본, `문서이력.xlsx`는 이력 기록이며,",
         f"> 질문셋은 `2_질문셋/`, 변경 예시·영향 라벨은 `3_변경시나리오/`에 따로 있습니다.", "",
         "## 1. 프로젝트", "", "| 항목 | 내용 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in P.OVERVIEW] + [
         f"| 수행사 | {company.COMPANY} |", "",
         "## 2. 조직과 역할", "",
         f"- 오너(PM): {pname(P.OWNER)}({P.OWNER}) — 프로젝트 생성·종료, PMO 문서 승인",
         f"- PMO 멤버: " + ", ".join(f"{pname(m)}({m})" for m in P.PMO[3]),
         "- 작성자 = 멤버, 승인자 = 소유 팀 팀장 (본인 승인 없음)", "",
         "| 팀 | 팀장 | 멤버 | 하는 일 | 소유 문서 | 주로 참조하는 문서 |", "|---|---|---|---|---|---|"]
    for code, name, ldr, members, job in P.TEAMS:
        own = ", ".join(s["name"] for s in P.DOCS.values() if s["team"] == code)
        refs = ", ".join(P.DOCS[r]["name"] for r in P.REFS[code])
        L.append(f"| {name} | {pname(ldr)}({ldr}) | " + ", ".join(f"{pname(m)}({m})" for m in members) + f" | {job} | {own} | {refs} |")
    L += ["", "게스트(발주처, 오너가 프로젝트 단위로 초대 — '외부 공유' 문서만 열람, MCP 불가):", ""] + [f"- {x[1]}({x[0]}) — {x[4]} {x[3]}, {x[2]}" for x in P.EXTERNAL]
    L += ["", "## 3. 문서 공개 범위 4단계", "", "> 261118 기획서 최종본 4-1 기준. 오너(PM)는 모든 문서를 볼 수 있습니다.", "",
          "| 공개 범위 | 열람 가능 |", "|---|---|"] + [f"| {g} | {w} |" for g, w in P.GRADES]
    L += ["", "## 4. 문서 목록과 HEAD (2026-11-18 기준)", "",
          "| No | 문서 | 소유 팀 | 작성자 | 승인자 | 공개 범위 | HEAD | HEAD 파일 |", "|---|---|---|---|---|---|---|---|"]
    for k, s in P.DOCS.items():
        L.append(f"| {s['no']:02d} | {s['name']} | {tn[s['team']]} | {pname(s['author'])} | {pname(lead(P)[s['team']])} | {s['grade']} | "
                 f"v{heads[k][0]} | `{heads[k][3].relative_to(out).as_posix()}` |")
    L += ["", "## 5. ID 체계와 참조 방향", "",
          "- 요구사항 FR-001~028 · NFR-001~008 → 업무 프로세스 P-01~07(BR·EX) → 화면 SCR-001~015 → 인터페이스 IF-001~038 → 테이블 TB_* → 테스트케이스 TC-001~038",
          "- 인터페이스는 담당 팀으로 문서가 나뉜다: 회원·상품 API(05), 주문·결제 API·배치(06), 외부·레거시 연계(07)",
          "- 요구사항정의서 '6. 요구사항 추적표'가 이 연결을 한 표로 보여 준다. `build_docset.py`의 `check()`가 참조가 끊기지 않았는지 검사한다.", "",
          "## 6. 폴더 구조", "", "```",
          f"{P.FOLDER}/", "  00_프로젝트개요_팀구성.md   이 파일", "  v1/        기준선 — 14개 문서 모두 v1",
          "  v2/, v3/   승인된 변경으로 생긴 그 버전의 문서만 (문서별 HEAD = 가장 높은 버전 폴더)",
          "  승인대기/  승인 담당자가 아직 처리하지 않은 제출본 (HEAD 아님, 승인 화면 비교용)",
          "  반려/      반려된 제출본 (HEAD 아님, 반려 사유는 문서이력.xlsx의 '변경 요청' 시트)",
          "  문서이력.xlsx  문서별 HEAD 현황 + 변경 요청 이력(승인·반려·대기)", "```", "",
          "## 7. 변경 요청 요약", "", "| 변경 ID | 문서 | 버전 | 상태 | 작성자 → 승인 담당 | 처리일 | 요약 |", "|---|---|---|---|---|---|---|"]
    for c, bv, nv, _ in log:
        s = P.DOCS[c["doc"]]
        L.append(f"| {c['id']} | {s['name']} | v{bv} → v{nv} | {c['status']} | {pname(c['author'])} → {pname(lead(P)[s['team']])} | {c['done'] or '-'} | {c['summary']} |")
    L += ["", "## 8. 반복되는 값 (현재 HEAD, 정규식 자동 검출)", "",
          "⚠️는 문서마다 값이 다르다는 뜻입니다(변경이 일부 문서에만 반영된 상태 등). 위치 전체는 `3_변경시나리오/` 엑셀의 '반복값 위치(HEAD)' 시트에 있습니다.", "",
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


def write_questions():
    by_code = {P.CODE: P for P in PROJECTS}
    wb = Workbook()
    wb.remove(wb.active)
    rows = []
    for n, (pc, q, intent, kind, asker, refs, note) in enumerate(questions.QUESTIONS, 1):
        P = by_code.get(pc, PROJECTS[0])
        code, role = roster(P).get(asker, ("-", "프로젝트 밖 사내 구성원"))
        team = team_name(P).get(code) or ("발주처" if role == "게스트" else "소속 팀 없음")
        rows.append((f"Q{n:03d}", pc, q, intent, kind, asker, f"{pname(asker)} · {team} · {role}", refs, note))
    xl_sheet(wb, "질문", f"사용자 질문 의도 평가셋 (DATA-07 초안, 데이터셋 개정 {PROJECTS[0].FOLDER[:8]})",
             ["질문 ID", "프로젝트", "질문", "의도(정답, 복수는 ;)", "유형", "질문자 사번", "질문자(이름·팀·역할)", "관련 문서·ID", "정답·비고"],
             rows, (8, 8, 48, 22, 7, 9, 28, 24, 60))
    counts = {}
    for q in questions.QUESTIONS:
        for i in q[2].split(";"):
            counts[i] = counts.get(i, 0) + 1
    kinds = {k: sum(q[3] == k for q in questions.QUESTIONS) for k in ("단일", "애매", "복합", "범위 밖")}
    xl_sheet(wb, "분포", "라벨 분포", ["구분", "값", "건수"],
             [("의도", k, counts.get(k, 0)) for k in sorted(questions.INTENTS)] + [("유형", k, v) for k, v in kinds.items()] +
             [("전체", "질문 수", len(questions.QUESTIONS))], (8, 14, 8))
    Q_DIR.mkdir(exist_ok=True)
    wb.save(Q_DIR / f"{PROJECTS[0].FOLDER}_질문셋.xlsx")


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
    for i in IF:
        assert set(i[8]) <= scr and set(i[9]) <= tbs and i[13] in ("MP", "OP", "CT"), i[0]
        assert i[13] == "CT" or i[2] in ("내부 API", "배치"), f"{i[0]} 외부 연계는 공통기술팀 소유"
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
                rt, rc = c[6].split(".")
                assert any(c2[0] == rc for x in TB if x[0] == rt for c2 in x[3]), (t[0], c[0])
    # 조직: 팀장 ≠ 멤버, 멤버 3명 이상, 작성자는 소유 팀 멤버(본인 승인 금지)
    ro, ld = roster(P), lead(P)
    for code, _, ldr, members, _ in P.TEAMS:
        assert len(members) >= 3 and ldr not in members, code
    for k, s in P.DOCS.items():
        assert s["grade"] in {g[0] for g in P.GRADES}, f"{k} 공개 범위"
        assert ro[s["author"]] == (s["team"], "멤버") and s["author"] != ld[s["team"]], f"{k} 작성자"
    for c in P.CHANGES:
        assert ro[c["author"]] == (P.DOCS[c["doc"]]["team"], "멤버"), f"{c['id']} 작성자는 소유 팀 멤버"
        assert c["id"] in P.IMPACT
    for q in questions.QUESTIONS:
        assert set(q[2].split(";")) <= questions.INTENTS, f"의도 라벨 오타: {q[1]}"
        assert q[4] in ro or q[4] in EMP, f"질문자 없음: {q[1]}"


if __name__ == "__main__":
    for P in PROJECTS:
        check(P)
        heads, log = build_project(P)
        print(f"{P.FOLDER}: 문서 {len(P.DOCS)} · FR {len(P.FR)} · NFR {len(P.NFR)} · 프로세스 {len(P.PROC)} · SCR {len(P.SCR)} · IF {len(P.IF)} · "
              f"TB {len(P.TB)} · TC {len(P.TC)} · 변경 {len(log)} · HEAD " + ", ".join(f"{k}=v{v[0]}" for k, v in heads.items()))
    write_company()
    write_questions()
    print(f"질문 {len(questions.QUESTIONS)} -> {ROOT}")
