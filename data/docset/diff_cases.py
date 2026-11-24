"""diff 노이즈·경계 케이스 (CHG-04 조정용) → 4_diff경계케이스/

build_docset.py가 문서 세트를 만든 뒤 호출한다. 케이스마다 HEAD 문서로 원본·수정본 한 쌍을 만들고,
diff가 '변경'으로 잡아야 하는지 정답을 diff경계케이스_정답.xlsx에 적는다.

  노이즈(N-): 텍스트 내용은 그대로 — diff에 잡히면 오류 (서식, 공백·줄바꿈·전각, 추출 순서)
  경계(X-):  서식·구조가 바뀌었지만 의미가 있을 수 있는 것 — 파이프라인 팀과 26.11 합의한 기준을 정답으로 쓴다
             숨김 열·행 = 변경 아님 / 수식 계산값 = 변경 / 취소선·빨간 글씨 = 변경 / 이미지 안 글자 = 대상 아님(OCR 후 검토)
             문단 이동 = 단순 이동·순서가 의미 있는 이동 모두 변경(유형 '이동')

원본은 수정본과 같은 방식(같은 라이브러리로 열고 저장)으로 만들어, 의도한 차이 말고는 두 파일이 같게 한다.
"""
import io
import re
import shutil
import zipfile
from xml.sax.saxutils import escape

from docx import Document
from docx.shared import Inches as DInches
from docx.shared import Pt
from docx.shared import RGBColor as DRGB
from docx.enum.text import WD_ALIGN_PARAGRAPH
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches

NO, YES, NA = "변경 없음", "변경 있음", "대상 아님"
AGREE = "26.11 파이프라인 팀 합의"


# ─────────────── 문서 안에서 찾기 ───────────────
def para(doc, start):
    return next(p for p in doc.paragraphs if p.text.startswith(start))


def cell(doc, text):
    return next(c for t in doc.tables for r in t.rows for c in r.cells if c.text == text)


def xrow(ws, key):
    return next(r for r in range(4, ws.max_row + 1) if ws.cell(r, 1).value == key)


def slide_of(prs, sid):
    return next(s for s in prs.slides if any(sh.has_text_frame and sh.text_frame.text.startswith(sid + "  ") for sh in s.shapes))


def png(text):
    from PIL import Image, ImageDraw, ImageFont  # python-pptx 의존성으로 설치돼 있다
    try:
        font = ImageFont.load_default(size=30)
    except TypeError:  # Pillow < 10.1
        font = ImageFont.load_default()
    img = Image.new("RGB", (560, 96), "white")
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((4, 4, 556, 92), 18, outline=(120, 120, 120), width=3, fill=(240, 240, 240))
    d.text((28, 30), text, fill=(40, 40, 40), font=font)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return buf


# ─────────────── 수정본 만드는 함수 (원본 객체를 고친다) ───────────────
def bold_para(doc):
    for r in para(doc, "본 문서는").runs:
        r.bold, r.font.size = True, Pt(12)


def blue_para(doc):
    for r in para(doc, "VSM 경계 밖 시스템은").runs:
        r.font.color.rgb = DRGB(0x1F, 0x4E, 0x79)


def layout_doc(doc):
    p = para(doc, "역할 기반 접근 제어")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.left_indent = DInches(0.5)
    doc.sections[0].left_margin = DInches(1.5)


def spaces(doc):
    r = para(doc, "본 문서는").runs[0]
    t = r.text.replace(" ", "  ", 1)  # 두 칸
    i = t.find(" ", 10)
    r.text = t[:i] + " " + t[i + 1:] + "   "  # 줄바꿈 없는 공백(NBSP) + 끝 공백


def soft_break(doc):
    p = para(doc, "VSM 경계 밖 시스템은")
    r = p.runs[0]
    i = r.text.find(" ", len(r.text) // 2)
    left, right = r.text[:i], r.text[i + 1:]
    r.text = left
    r.add_break()  # 문단은 그대로, 문단 안 줄바꿈(Shift+Enter)
    p.add_run(right)


def img_doc(text):
    def f(doc):
        doc.add_heading("부록. 배송비 안내 배지 시안", 1)
        doc.add_picture(png(text), width=DInches(4))
    return f


def strike_cell(doc):
    for p in cell(doc, "같은 이메일 계정이 여럿이면 최근 로그인 계정만 이행").paragraphs:
        for r in p.runs:
            r.font.strike = True


def red_cell(doc):
    for p in cell(doc, "배송비 3,000원, 쿠폰 적용 후 상품금액 50,000원 이상이면 무료, 제주·도서산간 +3,000원").paragraphs:
        for r in p.runs:
            r.font.color.rgb = DRGB(0xFF, 0x00, 0x00)


def swap_rows(doc):
    t = next(t for t in doc.tables if len(t.rows) > 2 and t.rows[1].cells[0].text == "저장 암호화")
    a, b = t.rows[1].cells, t.rows[2].cells
    for x, y in zip(a, b):
        x.text, y.text = y.text, x.text


FR = "2. 기능 요구사항"


def fmt_xlsx(wb):
    ws = wb[FR]
    r = xrow(ws, "FR-003")
    for c in ws[r]:
        c.fill, c.font = PatternFill("solid", fgColor="FFF2CC"), Font(name="맑은 고딕", size=10, bold=True)
    ws.column_dimensions["D"].width = 90
    ws.row_dimensions[r].height = 60


def fullwidth(wb):
    c = wb[FR].cell(xrow(wb[FR], "FR-012"), 4)
    c.value = c.value.translate(str.maketrans("0123456789,", "０１２３４５６７８９，"))


def memo(changed):
    def f(wb):
        ws = wb[FR]
        col = ws.max_column + 1
        ws.cell(3, col, "검토 메모")
        for r in range(4, ws.max_row + 1):
            ws.cell(r, col, "검토 완료")
        if changed:
            ws.cell(xrow(ws, "FR-003"), col, "보안팀 재검토 필요")
        ws.column_dimensions[ws.cell(3, col).column_letter].hidden = True
    return f


def hidden_row(wb):
    ws = wb["2. 컬럼 정의"]
    ws.append(["TB_REVIEW", "리뷰", 99, "DRAFT_MEMO", "작성메모(검토중)", "VARCHAR(200)", "Y", "", "", "검토 중인 초안 컬럼"])
    ws.row_dimensions[ws.max_row].hidden = True


def hide_fr(wb):
    ws = wb[FR]
    ws.row_dimensions[xrow(ws, "FR-008")].hidden = True


def strike_xlsx(wb):
    c = wb[FR].cell(xrow(wb[FR], "FR-008"), 4)
    c.font = Font(name="맑은 고딕", size=10, strike=True)


def move_codes(wb):
    ws = wb["3. 공통코드"]
    rows = [[c.value for c in ws[r]] for r in range(4, ws.max_row + 1)]
    rows = [r for r in rows if r[0] == "CARRIER"] + [r for r in rows if r[0] != "CARRIER"]  # 정렬 열은 그대로
    for i, vals in enumerate(rows, 4):
        for j, v in enumerate(vals, 1):
            ws.cell(i, j, v)


def nudge_slide(prs):
    s = slide_of(prs, "SCR-001")
    for sh in s.shapes:
        if sh.has_text_frame and re.match(r"\(\d+\) ", sh.text_frame.text):
            sh.left += Inches(0.15)
            sh.fill.fore_color.rgb = RGBColor(0xDD, 0xEB, 0xF7)


def zorder(prs):
    tree = slide_of(prs, "SCR-005").shapes._spTree
    shapes = [e for e in tree if e.tag.rsplit("}", 1)[-1] in ("sp", "graphicFrame", "pic", "grpSp", "cxnSp")]
    for e in shapes:
        tree.remove(e)
    for e in reversed(shapes):  # 위치는 그대로, 겹침 순서(=추출 순서)만 뒤집음
        tree.append(e)


def img_slide(text):
    def f(prs):
        slide_of(prs, "SCR-005").shapes.add_picture(png(text), Inches(7.6), Inches(6.2), width=Inches(3.2))
    return f


# zip 안 XML을 직접 고치는 경우(수식 캐시 값·한글 문서 서식을 그대로 두기 위해)
def zip_edit(member, old, new):
    def f(path):
        with zipfile.ZipFile(path) as z:
            items = [(i, z.read(i.filename)) for i in z.infolist()]
        hit = 0
        for n, (info, data) in enumerate(items):
            if info.filename == member:
                xml = data.decode("utf-8")
                hit = xml.count(old)
                items[n] = (info, xml.replace(old, new).encode("utf-8"))
        assert hit, f"{member}: '{old[:40]}' 없음"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for info, data in items:
                z.writestr(info, data)
    return f


def txt_noise(path):
    lines = path.read_text(encoding="utf-8").split("\n")
    out = []
    for i, ln in enumerate(lines):
        out.append(ln + ("  " if i % 3 == 0 and ln else ""))  # 줄 끝 공백
        if ln.startswith("==="):
            out.append("")  # 빈 줄 추가
    path.write_bytes("\r\n".join(out).encode("utf-8"))  # CRLF 줄바꿈


# ─────────────── 데이터를 바꿔 다시 렌더링하는 경우 ───────────────
def tc_result(hd):
    i = next(n for n, t in enumerate(hd["TC"]) if t[8] == "미수행")
    t = hd["TC"][i]
    hd["TC"][i] = t[:8] + ("Pass", "2026-11-24") + t[10:]
    return t[0]


def swap_steps(hd):
    i = next(n for n, p in enumerate(hd["PROC"]) if p[0] == "P-05")
    steps = list(hd["PROC"][i][4])
    steps[0], steps[1] = (1,) + steps[1][1:], (2,) + steps[0][1:]
    hd["PROC"][i] = hd["PROC"][i][:4] + (steps,) + hd["PROC"][i][5:]


# (ID, 분류, 항목, 프로젝트, 문서 키, 방식, 수정 함수, 바꾼 내용, 기대 결과, 기대 유형, 위치, 근거·비고)
CASES = [
    ("N-01", "노이즈", "서식만 변경(굵게·크기)", "A", "arch", "docx", bold_para,
     "'1. 개요' 첫 문단을 굵게, 10pt → 12pt", NO, "-", "1. 개요 > 문단1", "서식은 추적하지 않음(기획서 4장)"),
    ("N-02", "노이즈", "서식만 변경(글자색)", "A", "arch", "docx", blue_para,
     "'3. 시스템 경계' 문단 글자색을 파란색으로", NO, "-", "3. 시스템 경계와 외부·레거시 연계 > 문단1",
     "파란색 강조는 서식. 빨간 글씨(X-07)는 합의상 변경 표시로 본다 — 색으로 구분해야 함"),
    ("N-03", "노이즈", "레이아웃만 변경", "A", "arch", "docx", layout_doc,
     "'6. 권한 설계' 문단 가운데 정렬·들여쓰기, 페이지 왼쪽 여백 1.5인치", NO, "-", "6. 권한 설계 > 문단1", "레이아웃은 서식"),
    ("N-04", "노이즈", "서식만 변경(엑셀 칸)", "A", "req", "xlsx", fmt_xlsx,
     "FR-003 행 노란 배경·굵게, D열 너비 90, 행 높이 60", NO, "-", "2. 기능 요구사항 > FR-003", "칸 서식·열 너비·행 높이는 서식"),
    ("N-05", "노이즈", "레이아웃만 변경(PPT 도형)", "A", "scr", "pptx", nudge_slide,
     "SCR-001 슬라이드 구성요소 상자를 오른쪽으로 0.15인치, 채우기 색 변경", NO, "-", "SCR-001 슬라이드", "도형 위치·색은 서식"),
    ("N-06", "노이즈", "공백만 다름(두 칸·NBSP·끝 공백)", "A", "arch", "docx", spaces,
     "'1. 개요' 문단의 띄어쓰기 한 곳을 두 칸, 한 곳을 NBSP로, 문단 끝 공백 3개", NO, "-", "1. 개요 > 문단1",
     "공백 종류·개수 차이는 정규화로 같게 본다. 단, 없던 띄어쓰기가 생기는 것('주문상태'→'주문 상태')은 텍스트 변경(TR-A-021)"),
    ("N-07", "노이즈", "문단 안 줄바꿈", "A", "arch", "docx", soft_break,
     "'3. 시스템 경계' 문단 중간의 띄어쓰기를 문단 안 줄바꿈(Shift+Enter)으로", NO, "-", "3. 시스템 경계와 외부·레거시 연계 > 문단1",
     "줄바꿈도 공백으로 정규화"),
    ("N-08", "노이즈", "전각/반각 차이", "A", "req", "xlsx", fullwidth,
     "FR-012 상세 설명의 숫자·콤마를 전각으로(70,000 → ７０，０００)", NO, "-", "2. 기능 요구사항 > FR-012 > 상세 설명",
     "NFKC 정규화로 같은 문자"),
    ("N-09", "노이즈", "줄바꿈 코드·끝 공백·빈 줄(txt)", "B", "mig", "txt", txt_noise,
     "LF → CRLF, 세 줄마다 줄 끝 공백 2개, 제목 밑줄 뒤 빈 줄 추가", NO, "-", "문서 전체", "공백·빈 줄은 정규화"),
    ("N-10", "노이즈", "PDF 추출 순서 흔들림", "B", "arch", "pdf_shuffle", None,
     "페이지 안 텍스트를 그리는 순서만 역순(화면은 같음)", NO, "-", "문서 전체",
     "PDF는 그리는 순서대로 추출되기 쉬움 — 위치(좌표) 기준으로 정렬해야 함"),
    ("N-11", "노이즈", "PPT 추출 순서 흔들림", "A", "scr", "pptx", zorder,
     "SCR-005 슬라이드 도형의 겹침 순서만 역순(위치는 그대로)", NO, "-", "SCR-005 슬라이드",
     "PPT는 도형 저장 순서대로 추출됨 — 슬라이드 안 위치 기준으로 정렬해야 함"),
    ("N-12", "노이즈", "서식만 변경(한글 문서)", "B", "pol", "zip", None,
     "'2. 발주 승인 한도' 첫 문단의 글자 모양을 11pt 굵게로", NO, "-", "2. 발주 승인 한도 > 문단1", "hwpx 글자 모양(charPr)은 서식"),
    ("X-01", "경계", "숨김 열 값 변경", "A", "req", "xlsx2", (memo(False), memo(True)),
     "원본·수정본 모두 숨김 열 '검토 메모'가 있고, 수정본에서 FR-003 메모만 '검토 완료' → '보안팀 재검토 필요'", NO, "-",
     "2. 기능 요구사항 > FR-003 > 검토 메모(숨김 열)", f"{AGREE}: 숨김 열·행은 diff 아님"),
    ("X-02", "경계", "숨김 행 추가", "A", "tb", "xlsx", hidden_row,
     "'2. 컬럼 정의' 끝에 초안 컬럼 행(TB_REVIEW.DRAFT_MEMO)을 숨김 상태로 추가", NO, "-", "2. 컬럼 정의 > 마지막 행(숨김)",
     f"{AGREE}: 숨김 열·행은 diff 아님"),
    ("X-03", "경계", "기존 행을 숨김 처리", "A", "req", "xlsx", hide_fr,
     "FR-008 행을 숨김(값은 그대로)", NO, "-", "2. 기능 요구사항 > FR-008",
     f"{AGREE}상 '변경 없음'. 다만 화면에서는 요구사항이 사라진 것과 같아 합의 재확인 필요"),
    ("X-04", "경계", "참조 값이 바뀌어 수식 계산값이 바뀜", "B", "tc", "data", tc_result,
     "'1. 테스트케이스'에서 수행 결과 1건 미수행 → Pass(수행일 입력). '3. 수행 요약'의 COUNTIFS·SUM·Pass율 수식은 그대로, 계산값만 바뀜", YES, "수정",
     "1. 테스트케이스 > {id} > 수행 결과·수행일 + 3. 수행 요약(수식 셀 계산값)", f"{AGREE}: 계산값 기준으로 비교 — 수식 셀도 변경으로 잡는다"),
    ("X-05", "경계", "수식만 바뀌고 계산값은 같음", "B", "wbs", "zip", None,
     "'1. WBS' H6 수식 =G6-F6+1 → =(G6-F6)+1 (계산값 같음)", NO, "-", "1. WBS > H6(기간)", f"{AGREE}: 계산값 기준 비교 → 값이 같으면 변경 아님"),
    ("X-06", "경계", "취소선(삭제 표시)", "A", "proc", "docx", strike_cell,
     "P-02 업무 규칙 BR-06 내용에 취소선", YES, "삭제 표시(취소선)", "3. 프로세스 상세 > P-02 기존 회원 전환 > 업무 규칙 > BR-06",
     f"{AGREE}: 취소선은 변경. 기획서 4장 '서식은 추적하지 않음'의 예외 — 기획서·명세서 갱신 필요"),
    ("X-07", "경계", "빨간 글씨(변경 표시)", "A", "proc", "docx", red_cell,
     "P-04 업무 규칙 BR-12 내용을 빨간 글씨로", YES, "변경 표시(빨간 글씨)", "3. 프로세스 상세 > P-04 주문·결제 > 업무 규칙 > BR-12",
     f"{AGREE}: 빨간 글씨는 변경. 파란색 등 다른 색(N-02)은 서식 — 색으로 구분해야 함"),
    ("X-08", "경계", "취소선(엑셀 칸)", "A", "req", "xlsx", strike_xlsx,
     "FR-008 상세 설명 칸에 취소선", YES, "삭제 표시(취소선)", "2. 기능 요구사항 > FR-008 > 상세 설명", f"{AGREE}: 취소선은 변경"),
    ("X-09", "경계", "이미지 안 글자(워드)", "A", "arch", "docx2", (img_doc("FREE SHIPPING 50,000 KRW+"), img_doc("FREE SHIPPING 70,000 KRW+")),
     "부록에 넣은 배지 이미지 안 글자만 50,000 → 70,000", NA, "-", "부록. 배송비 안내 배지 시안 > 그림",
     f"{AGREE}: OCR 도입 후 검토. 지금은 텍스트 diff 없음이 정상 — 사례만 보관"),
    ("X-10", "경계", "이미지 안 글자(PPT)", "A", "scr", "pptx2", (img_slide("FREE SHIPPING 50,000 KRW+"), img_slide("FREE SHIPPING 70,000 KRW+")),
     "SCR-005 슬라이드에 넣은 배지 이미지 안 글자만 50,000 → 70,000", NA, "-", "SCR-005 슬라이드 > 그림",
     f"{AGREE}: OCR 도입 후 검토 — 사례만 보관"),
    ("X-11", "경계", "단순 이동(워드 표 행)", "A", "arch", "docx", swap_rows,
     "'7. 보안 설계' 표의 '저장 암호화'·'전송 구간' 행 순서만 바꿈", YES, "이동", "7. 보안 설계 > 저장 암호화, 전송 구간",
     f"{AGREE}: 단순 이동도 변경(유형 '이동'). 판정 입력에서 삭제+추가로 쪼개지 않게 할 것"),
    ("X-12", "경계", "단순 이동(엑셀 행)", "A", "tb", "xlsx", move_codes,
     "'3. 공통코드'에서 CARRIER 코드 2행을 표 맨 위로(정렬 열 값은 그대로)", YES, "이동", "3. 공통코드 > CARRIER",
     f"{AGREE}: 단순 이동도 변경(유형 '이동')"),
    ("X-13", "경계", "순서가 의미 있는 이동(흐름 변경)", "A", "proc", "data", swap_steps,
     "P-05 To-Be 단계 1·2의 내용 순서를 바꿈(번호는 1·2 그대로) → 출고 지시가 상품준비중 변경보다 먼저", YES, "이동(흐름 변경)",
     "3. 프로세스 상세 > P-05 출고·배송 > To-Be 업무 흐름 > 1·2", f"{AGREE}: 변경. 시나리오 유형 '흐름 변경'과 연결 — 영향 판정 대상"),
]

ZIP_EDITS = {  # 케이스 ID → (zip 안 파일, 원래 문자열, 바꿀 문자열)
    "N-12": ("Contents/section0.xml",
             '<hp:run charPrIDRef="0"><hp:t>' + escape("발주 결재선은 부가세를 뺀"),
             '<hp:run charPrIDRef="3"><hp:t>' + escape("발주 결재선은 부가세를 뺀")),
    "X-05": ("xl/worksheets/sheet2.xml", "<f>G6-F6+1</f>", "<f>(G6-F6)+1</f>"),
}


def build(B, built):
    out = B.ROOT / "4_diff경계케이스"
    out.mkdir(exist_ok=True)
    for f in out.iterdir():
        f.unlink()
    rows = []
    for cid, cls, item, pc, k, how, fn, what, exp, typ, loc, note in CASES:
        P, heads, hist = built[pc]
        s, src = P.DOCS[k], heads[k][3]
        ext = src.suffix
        o, m = out / f"{cid}_원본{ext}", out / f"{cid}_수정본{ext}"
        if how in ("docx", "docx2", "xlsx", "xlsx2", "pptx", "pptx2"):
            load = {"d": Document, "x": load_workbook, "p": Presentation}[how[0]]
            fo, fm = fn if how.endswith("2") else (None, fn)
            for path, f in ((o, fo), (m, fm)):
                obj = load(src)
                if f:
                    f(obj)
                obj.save(path)
        else:
            shutil.copyfile(src, o)
            if how == "zip":
                shutil.copyfile(src, m)
                zip_edit(*ZIP_EDITS[cid])(m)
            elif how == "txt":
                shutil.copyfile(src, m)
                fn(m)
            else:  # data · pdf_shuffle: HEAD와 같은 메타로 다시 렌더링
                hd = B.head_data(P)
                ret = fn(hd) if fn else None
                kind, body = B.MODELS[s["model"]](P, hd, s)
                meta = B.meta_of(P, s, f"v{heads[k][0]}", "HEAD 승인본", hist[k], heads[k][5])
                if how == "pdf_shuffle":
                    B.render_pdf(m, meta, body, shuffle=True)
                else:
                    assert B.diff(kind, heads[k][2], body), cid
                    B.RENDER[s.get("fmt", kind)](m, meta, body)
                    loc = loc.replace("{id}", ret or "")
        rows.append((cid, cls, item, ext[1:], f"{P.FOLDER}/{src.relative_to(B.DOC_DIR / P.FOLDER).as_posix()}",
                     o.name, m.name, what, exp, typ, loc, note))
    wb = B.Workbook()
    ws = wb.active
    ws.title = "안내"
    for r in [["diff 노이즈·경계 케이스 — 파이프라인 diff(CHG-04) 조정용. 영향 판정 라벨은 없다"], [],
              ["케이스마다 원본·수정본 한 쌍이다. 원본은 1_문서세트의 HEAD 문서(같은 라이브러리로 열고 저장한 것), 수정본은 거기서 한 가지만 바꿨다."],
              ["노이즈(N-): 텍스트 내용은 같다. diff 결과가 비어야 정답."],
              [f"경계(X-): 서식·구조 변경 중 의미가 있을 수 있는 것. 정답은 {AGREE} 기준."],
              ["  숨김 열·행 = 변경 아님 / 수식 계산값 = 변경 / 취소선·빨간 글씨 = 변경 / 이미지 안 글자 = 대상 아님(OCR 도입 후 검토) / 문단 이동 = 변경(유형 '이동')"],
              ["채점: diff 결과가 '기대 결과'와 같고, 변경이면 '기대 유형'·'위치'가 맞는지 본다."], [],
              ["주의: N-02(파란 글씨 = 서식)와 X-07(빨간 글씨 = 변경)은 색으로만 갈린다. X-03(기존 행 숨김)은 합의 기준상 변경 없음이지만 재확인이 필요하다."]]:
        ws.append(r)
    ws["A1"].font = Font(name=B.FONT, bold=True, size=14)
    ws.column_dimensions["A"].width = 130
    B.xl_sheet(wb, "케이스", "diff 노이즈·경계 케이스 정답",
               ["케이스 ID", "분류", "항목", "형식", "원본 문서(HEAD)", "원본 파일", "수정본 파일", "바꾼 내용", "기대 결과", "기대 유형", "위치", "근거·비고"],
               rows, (8, 7, 24, 6, 36, 18, 18, 50, 10, 16, 40, 50))
    wb.save(out / "diff경계케이스_정답.xlsx")
    return len(rows)
