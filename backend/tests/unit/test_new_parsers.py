"""parsing/new 포맷별 파서 테스트. 실행 (backend 폴더에서):  uv run python -m pytest tests/unit/test_new_parsers.py"""

from pathlib import Path

import pytest
from docx import Document
from docx.oxml import parse_xml
from openpyxl import Workbook
from pptx import Presentation
from pptx.util import Pt

from app.pipeline.models import BlockKind
from app.pipeline.parsing.docling.base import ParseError
from app.pipeline.parsing.structured import parser_for


def _parse(path: Path):
    return parser_for(str(path)).parse(str(path)).blocks


def test_docx_order_headings_caption_merge_nesting_and_textbox(tmp_path: Path):
    document = Document()
    document.add_heading("1장", level=1)
    document.add_paragraph("항목 하나", style="List Bullet")
    document.add_paragraph("표 1. 권한")
    table = document.add_table(rows=2, cols=3)
    table.cell(0, 0).text, table.cell(0, 1).text = "구분", "내용"
    table.cell(0, 1).merge(table.cell(0, 2))
    table.cell(1, 0).text = "A"
    cell = table.cell(1, 1).merge(table.cell(1, 2))
    for level in range(1, 4):       # 표 안의 표 안의 표 안의 표
        inner = cell.add_table(rows=2, cols=2)
        inner.cell(0, 0).text, inner.cell(0, 1).text = "키", "값"
        inner.cell(1, 0).text = f"깊이{level}"
        cell = inner.cell(1, 1)
    cell.text = "바닥"
    box = document.add_paragraph("본문")
    box._p.append(parse_xml(
        '<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:pict><w:txbxContent><w:p><w:r><w:t>글상자 글</w:t></w:r></w:p></w:txbxContent></w:pict></w:r>"
    ))
    document.add_heading("2장", level=1)
    path = tmp_path / "t.docx"
    document.save(path)

    blocks = _parse(path)
    texts = [b.text for b in blocks]
    assert blocks[0].kind == BlockKind.HEADING and blocks[1].kind == BlockKind.LIST_ITEM
    assert texts.count("표 1. 권한") == 1 and blocks[2].kind == BlockKind.TABLE_TITLE
    assert texts.index("본문") + 1 == texts.index("글상자 글")
    assert all(any(v in t for t in texts) for v in ["깊이1", "깊이2", "깊이3", "바닥"])
    assert max(b.location.parent_table_index or 0 for b in blocks) >= 1
    assert blocks[-1].heading_path == ("2장",)


def _textbox(slide, text, left, top, width=2540000, size=None):
    shape = slide.shapes.add_textbox(left, top, width, Pt(30))
    shape.text_frame.text = text
    if size:
        shape.text_frame.paragraphs[0].runs[0].font.size = Pt(size)
    return shape


def test_pptx_columns_groups_title_split_cells_and_hidden_slide(tmp_path: Path):
    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    # 만든 순서는 오른쪽이 먼저
    _textbox(slide, "설명", Pt(400), Pt(100))
    group = slide.shapes.add_group_shape()
    for i, top in enumerate((100, 200, 300), start=1):
        _textbox(group, f"({i})", Pt(20), Pt(top), size=12)
    table = slide.shapes.add_table(3, 3, Pt(400), Pt(150), Pt(250), Pt(100)).table
    table.cell(0, 1).merge(table.cell(0, 2))
    table.cell(1, 1).merge(table.cell(1, 2))
    for (r, c), value in {
        (0, 0): "ID", (0, 1): "화면명", (1, 0): "1", (1, 1): "회원가입",
        (2, 0): "2", (2, 1): "로그인", (2, 2): "분리",
    }.items():
        table.cell(r, c).text = value
    _textbox(slide, "화면 제목", Pt(20), Pt(10), Pt(600), size=28)
    hidden = deck.slides.add_slide(deck.slide_layouts[6])
    _textbox(hidden, "숨김", 0, 0)
    hidden._element.set("show", "0")
    path = tmp_path / "t.pptx"
    deck.save(path)

    blocks = _parse(path)
    texts = [b.text for b in blocks]
    assert texts[:5] == ["화면 제목", "(1)", "(2)", "(3)", "설명"]
    assert "ID  |  화면명" in texts
    assert "ID: 1  |  화면명: 회원가입" in texts
    assert "ID: 2  |  화면명: [분리 셀] 로그인 / 분리" in texts
    assert "숨김" not in texts


def test_xlsx_merged_header(tmp_path: Path):
    workbook = Workbook()
    for row in [["코드", "이름"], ["A01", "사과"]]:
        workbook.active.append(row)
    path = tmp_path / "t.xlsx"
    workbook.save(path)
    assert "코드: A01  |  이름: 사과" in [b.text for b in _parse(path)]


@pytest.mark.parametrize("name", ["old.doc", "old.ppt", "old.xls"])
def test_old_formats_are_rejected(name: str):
    with pytest.raises(ParseError):
        parser_for(name)


def test_broken_file_raises_parse_error(tmp_path: Path):
    path = tmp_path / "broken.docx"
    path.write_bytes(b"not a zip")
    with pytest.raises(ParseError):
        _parse(path)
