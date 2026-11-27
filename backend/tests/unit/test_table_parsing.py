"""표 파싱 회귀 테스트. 시험 문서는 테스트 안에서 만든다 (모델 다운로드가 필요한 PDF 변환은 제외).

실행 (backend 폴더에서):  uv run pytest tests/unit/test_table_parsing.py
"""

from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import pytest
from docling_core.types.doc import BoundingBox, DocItemLabel, DoclingDocument, ProvenanceItem, Size
from docx import Document
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.table import Table
from pypdfium2 import PdfDocument
from pptx import Presentation
from pptx.util import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from app.pipeline.models import Block, BlockKind, Location, ParsedDocument
from app.pipeline.parsing.docling.docling_parser import DoclingParser, _format_result, _reading_order
from app.pipeline.parsing.docling.docx_tables import _Styles, read_word_table
from app.pipeline.parsing.structured import parser_for
from app.pipeline.parsing.structured.pdf_parser import PdfParser as StructuredPdfParser, find_tables
from app.pipeline.parsing.docling.pdf_tables import (
    find_missing_pdf_tables, page_chars, read_camelot_tables, read_pdf_tables, repair_pdf_grid,
)
from app.pipeline.parsing.docling.table_grid import Grid, GridCell, grid_blocks, is_caption


def _blocks(grid: Grid):
    numbers = iter(range(100))
    return grid_blocks(grid, Location(), (), lambda: next(numbers))


def _texts(blocks, kind: BlockKind) -> list[str]:
    return [block.text for block in blocks if block.kind == kind]


def _grid(rows: list[list[str | None]], **options) -> Grid:
    cells = [
        GridCell(r, c, r + 1, c + 1, value)
        for r, row in enumerate(rows) for c, value in enumerate(row) if value is not None
    ]
    return Grid(len(rows), len(rows[0]), cells, **options)


def _word_blocks(build):
    document = Document()
    table = build(document)
    return _blocks(read_word_table(table._tbl, _Styles(document)))


def test_two_row_header_from_merged_cells():
    def build(document):
        table = document.add_table(rows=3, cols=3)
        for r, row in enumerate([["구분", "일정", ""], ["", "시작", "종료"], ["설계", "3/1", "3/5"]]):
            for c, value in enumerate(row):
                table.cell(r, c).text = value
        table.cell(0, 1).merge(table.cell(0, 2))
        table.cell(0, 0).merge(table.cell(1, 0))
        return table

    blocks = _word_blocks(build)
    assert _texts(blocks, BlockKind.TABLE_HEADER) == ["구분  |  일정\n일정: 시작 / 종료"]
    assert {cell.range for cell in blocks[0].group_cells} == {"A1:A2", "B1:C1"}
    assert _texts(blocks, BlockKind.TABLE_ROW) == ["구분: 설계  |  일정: [분리 셀] 3/1 / 3/5"]


@pytest.mark.parametrize("structured", [False, True])
def test_four_level_nested_word_table_keeps_every_value(tmp_path: Path, structured: bool):
    def build(document):
        outer = document.add_table(rows=2, cols=2)
        outer.cell(0, 0).text, outer.cell(0, 1).text = "구분", "상세"
        outer.cell(1, 0).text = "회원"
        middle = outer.cell(1, 1).add_table(rows=2, cols=2)
        middle.cell(0, 0).text, middle.cell(0, 1).text = "항목", "값"
        middle.cell(1, 0).text = "로그인"
        inner = middle.cell(1, 1).add_table(rows=2, cols=2)
        inner.cell(0, 0).text, inner.cell(0, 1).text = "설정", "상세"
        inner.cell(1, 0).text = "계정"
        inner.cell(1, 1).paragraphs[0].text = "표 1. 계정 자료"
        deepest = inner.cell(1, 1).add_table(rows=2, cols=2)
        for r, row in enumerate([["키", "타입"], ["userId", "string"]]):
            for c, value in enumerate(row):
                deepest.cell(r, c).text = value
        return outer

    document = Document()
    build(document)
    path = tmp_path / "nested.docx"
    document.save(path)
    parser = parser_for(str(path)) if structured else DoclingParser()
    blocks = parser.parse(str(path)).blocks
    joined = " ".join(block.text for block in blocks)
    assert all(value in joined for value in ["회원", "로그인", "계정", "키", "userId", "string"])
    assert [b.location.parent_table_index for b in blocks if b.text.startswith("키: userId")] == [2]
    assert _texts(blocks, BlockKind.TABLE_TITLE) == ["표 1. 계정 자료"]


@pytest.mark.parametrize("structured", [False, True])
def test_four_level_borderless_pptx_tables_keep_merges_and_rows(tmp_path: Path, structured: bool):
    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    left, top, width, height = 100000, 100000, 8000000, 5400000
    for level in range(4):
        table = slide.shapes.add_table(3, 2, left, top, width, height).table
        table.cell(0, 0).merge(table.cell(0, 1))
        table.cell(0, 0).text = f"Table {level + 1}"
        table.cell(1, 0).text, table.cell(1, 1).text = "Key", "Detail"
        table.cell(2, 0).text = f"Value {level + 1}"
        left += width // 2
        top += 2 * height // 3 + 100
        width = width // 2 - 100
        height = height // 3 - 100
    path = tmp_path / "nested.pptx"
    deck.save(path)
    parser = parser_for(str(path)) if structured else DoclingParser()
    result = parser.parse(str(path))
    assert _texts(result.blocks, BlockKind.TABLE_TITLE) == [f"Table {i}" for i in range(1, 5)]
    assert _texts(result.blocks, BlockKind.TABLE_HEADER) == ["Key  |  Detail"] * 4
    assert [b.location.parent_table_index for b in result.blocks if b.kind == BlockKind.TABLE_TITLE] == [
        None, 0, 1, 2,
    ]


def test_headerless_key_value_table():
    blocks = _blocks(_grid([["작성자", "홍길동"], ["작성일", "2026-01-01"]]))
    assert not _texts(blocks, BlockKind.TABLE_HEADER)
    assert _texts(blocks, BlockKind.TABLE_ROW)[0] == "열1: 작성자  |  열2: 홍길동"


def test_only_split_rows_get_split_cell_label():
    grid = Grid(4, 3, [
        GridCell(0, 0, 1, 1, "항목"), GridCell(0, 1, 1, 3, "내용"),
        GridCell(1, 0, 2, 1, "A"), GridCell(1, 1, 2, 3, "한 칸"),
        GridCell(2, 0, 3, 1, "B"), GridCell(2, 1, 3, 2, "왼쪽"), GridCell(2, 2, 3, 3, "오른쪽"),
        GridCell(3, 0, 4, 1, "C"), GridCell(3, 2, 4, 3, "하나뿐"),
    ])
    blocks = _blocks(grid)
    assert _texts(blocks, BlockKind.TABLE_HEADER) == ["항목  |  내용"]
    assert _texts(blocks, BlockKind.TABLE_ROW) == [
        "항목: A  |  내용: 한 칸",
        "항목: B  |  내용: [분리 셀] 왼쪽 / 오른쪽",
        "항목: C  |  내용: 하나뿐",
    ]
    assert blocks[-1].context == "항목, 내용"


@pytest.mark.parametrize("fmt", ["docx", "pptx", "pdf", "xlsx"])
def test_first_row_alone_defines_logical_columns(fmt):
    grid = Grid(3, 6, [
        GridCell(0, 0, 1, 2, "프로세스 ID"), GridCell(0, 2, 1, 3, "프로세스명"),
        GridCell(0, 3, 1, 4, "담당 개발팀"), GridCell(0, 4, 1, 5, "관련 요구사항"),
        GridCell(1, 0, 2, 1, "P-01"), GridCell(1, 1, 2, 2, "나나"),
        GridCell(1, 2, 2, 4, "회원 가입·인증\n회원·상품 업무개발"),
        GridCell(1, 4, 2, 5, "FR-001"),
        GridCell(2, 0, 3, 2, "P-02"), GridCell(2, 4, 3, 5, "FR-002"),
        GridCell(2, 5, 3, 6, "추가 원본 값"),
    ], header_hint=1)
    scope = {"pdf": {"page": 1}, "pptx": {"slide": 1}, "xlsx": {"sheet": "Sheet1"}}.get(fmt, {})
    blocks = grid_blocks(grid, Location(**scope), (), iter((0,)).__next__, preserve_structure=True)
    header, first_row, second_row = blocks
    assert header.table_columns == ("프로세스 ID", "프로세스명", "담당 개발팀", "관련 요구사항")
    assert first_row.table_rows[0] == (
        "P-01\n나나", "회원 가입·인증\n회원·상품 업무개발", None, "FR-001",
    )
    assert [(cell.range, cell.column_indexes) for cell in first_row.table_cells] == [
        ("A2", (0,)), ("B2", (0,)), ("C2:D2", (1, 2)), ("E2", (3,)),
    ]
    assert "프로세스 ID: [분리 셀] P-01 / 나나" in first_row.text
    assert second_row.table_cells[-1].column_indexes == ()
    assert "추가 원본 값" in second_row.text
    output = _format_result(f"example.{fmt}", ParsedDocument(tuple(blocks), fmt))
    assert "병합 셀 A1:B1" not in output


def test_split_beside_vertical_merge_keeps_source_spans():
    grid = Grid(3, 3, [
        GridCell(0, 0, 1, 1, "항목"), GridCell(0, 1, 1, 3, "내용"),
        GridCell(1, 0, 2, 1, "A"), GridCell(1, 1, 3, 2, "공통"), GridCell(1, 2, 2, 3, "위"),
        GridCell(2, 0, 3, 1, "B"), GridCell(2, 2, 3, 3, "아래"),
    ])
    block = next(b for b in _blocks(grid) if b.kind == BlockKind.TABLE_ROW_GROUP)
    assert "내용: [분리 셀] 공통 / 위" in block.text
    assert "내용: 아래" in block.text
    assert [(c.range, c.column_indexes) for c in block.table_cells if c.column_indexes == (1,)] == [
        ("B2:B3", (1,)), ("C2", (1,)), ("C3", (1,)),
    ]


def test_separate_headers_with_same_name_stay_distinct():
    blocks = _blocks(_grid([["항목", "비고", "비고"], ["A", "x", "y"], ["B", None, "z"]]))
    assert _texts(blocks, BlockKind.TABLE_HEADER) == ["항목  |  비고(1)  |  비고(2)"]
    assert _texts(blocks, BlockKind.TABLE_ROW)[1] == "항목: B  |  비고(2): z"


def test_multi_pair_table_reads_as_name_value():
    grid = _grid([
        ["화면 ID", "SCR-001", "화면명", "로그인"],
        ["사용자", "비회원", "", ""],
    ], header_hint=1)
    for cell in grid.cells:
        cell.shaded = cell.row == 0
    blocks = _blocks(grid)
    assert not _texts(blocks, BlockKind.TABLE_HEADER)
    assert _texts(blocks, BlockKind.TABLE_ROW) == ["화면 ID: SCR-001  |  화면명: 로그인", "사용자: 비회원"]


def test_column_headers_with_ids_are_not_a_pair_table():
    blocks = _blocks(_grid([["항목", "A01", "A02", "A03"], ["가격", "1", "2", "3"]]))
    assert _texts(blocks, BlockKind.TABLE_HEADER) == ["항목  |  A01  |  A02  |  A03"]


def test_slide_reading_order_is_left_column_first():
    boxes = {
        "제목": (0, 0, 100, 10),
        "설명": (60, 20, 90, 25), "설명표": (60, 30, 100, 55),
        "(1)": (5, 22, 50, 30), "(2)": (5, 35, 50, 45), "(3)": (5, 60, 50, 70),
    }
    ordered = _reading_order([(box, name) for name, box in boxes.items()])
    assert [name for _box, name in ordered] == ["제목", "(1)", "(2)", "(3)", "설명", "설명표"]


def test_caption_pattern():
    assert is_caption("표 1. 일정")
    assert is_caption("[표 2-1] 권한")
    assert not is_caption("표 1과 같이 처리한다.")


def test_xlsx_blank_row_hidden_row_and_two_row_header(tmp_path: Path):
    workbook = Workbook()
    sheet = workbook.active
    for row in [["코드", "이름"], ["A01", "사과"], [None, None], ["A02", "배"]]:
        sheet.append(row)
    sheet.append(["A03", "비밀"])
    sheet.row_dimensions[5].hidden = True
    second = workbook.create_sheet("일정")
    for row in [["구분", "일정", None], [None, "시작", "종료"], ["설계", "3/1", "3/5"]]:
        second.append(row)
    for cell in [*second[1], *second[2]]:
        cell.font = Font(bold=True)
    second.merge_cells("B1:C1")
    second.merge_cells("A1:A2")
    path = tmp_path / "t.xlsx"
    workbook.save(path)

    result = DoclingParser().parse(str(path))
    assert _texts(result.blocks, BlockKind.TABLE_HEADER) == ["코드  |  이름", "구분  |  일정\n일정: 시작 / 종료"]
    rows = _texts(result.blocks, BlockKind.TABLE_ROW)
    assert "코드: A02  |  이름: 배" in rows
    assert not any("비밀" in row for row in rows)
    assert any("숨긴" in warning for warning in result.warnings)


def _write_pdf(path: Path, stream: str) -> None:
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [5 0 R] /Count 1 >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R "
        "/Resources << /Font << /F1 3 0 R >> >> >>",
    ]
    data, offsets = b"%PDF-1.4\n", []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(data))
        data += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")
    start = len(data)
    data += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    data += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    data += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF".encode()
    path.write_bytes(data)


@pytest.mark.parametrize("parser", [DoclingParser(), StructuredPdfParser()])
def test_pdf_nested_table_is_attached_to_parent_cell(tmp_path: Path, parser):
    def line(x0, y0, x1, y1):
        return f"{x0} {y0} m {x1} {y1} l S"

    def text(x, y, value):
        return f"BT /F1 10 Tf {x} {y} Td ({value}) Tj ET"

    parts = ["0.8 w"]
    for level in range(4):
        left, bottom, right, top = 50 + level * 80, 510 + level * 8, 550 - level * 8, 740 - level * 32
        split = left + 72
        parts += [line(left, y, right, y) for y in (bottom, top - 24, top)]
        parts += [line(x, bottom, x, top) for x in (left, split, right)]
        parts += [
            text(left + 5, top - 16, "Key"), text(split + 5, top - 16, "Detail"),
            text(left + 5, top - 41, f"Value{level + 1}"),
        ]
        if level == 3:
            parts.append(text(split + 5, top - 41, "string"))
    path = tmp_path / "nested.pdf"
    _write_pdf(path, "\n".join(parts))

    with PdfDocument(path) as source, closing(source[0]) as page:
        chars = page_chars(page)
        tables = read_pdf_tables(page, chars)
        recovered = find_missing_pdf_tables(page, chars, [])
        assert len(recovered) == 1
        assert find_missing_pdf_tables(page, chars, [tables[0].box]) == []
        doc = DoclingDocument(name="nested")
        doc.add_page(page_no=1, size=Size(width=595, height=842))
        doc.add_text(
            DocItemLabel.TEXT, "Value1",
            prov=ProvenanceItem(
                page_no=1, bbox=BoundingBox(l=54, t=135, r=100, b=147), charspan=(0, 6),
            ),
        )
        recovered_blocks = parser._walk(str(path), "pdf", doc, (source, [chars]), [])
        assert not _texts(recovered_blocks, BlockKind.PARAGRAPH)
        assert sum(b.kind == BlockKind.TABLE_HEADER for b in recovered_blocks) == 4
    assert len(tables) == 1
    blocks = _blocks(tables[0].grid)
    rows = [b for b in blocks if b.text.startswith("Key: Value")]
    assert [b.location.parent_table_index for b in rows] == [None, 0, 1, 2]
    assert [b.location.parent_table_cell for b in rows] == [None, "B2", "B2", "B2"]
    assert rows[-1].text == "Key: Value4  |  Detail: string"

    

def test_pdf_borderless_repair_keeps_docling_when_columns_are_correct(tmp_path: Path):
    rows = [["Code", "Name"], ["A01", "Apple"], ["A02", "Pear"]]
    path = tmp_path / "borderless.pdf"
    _write_pdf(path, "\n".join(
        f"BT /F1 10 Tf {x} {700 - r * 20} Td ({value}) Tj ET"
        for r, row in enumerate(rows) for x, value in zip((60, 200), row)
    ))
    box = (50, 130, 250, 190)
    with PdfDocument(path) as source, closing(source[0]) as page:
        chars = page_chars(page)
        correct = _grid(rows)
        assert repair_pdf_grid(correct, page, box, chars) is correct
        collapsed = _grid([[" ".join(row)] for row in rows])
        repaired = repair_pdf_grid(collapsed, page, box, chars)
        assert len(find_missing_pdf_tables(page, chars, [], [(50, 110, 250, 130)])) == 1
        assert len(find_tables(page, chars, [], [])) == 1
        assert not find_tables(page, chars, [box], [])
    assert repaired.columns == 2
    assert [cell.text for cell in repaired.cells] == [value for row in rows for value in row]


def test_new2_pdf_parses_native_tables_when_model_is_unavailable(tmp_path, monkeypatch):
    path = tmp_path / "offline.pdf"
    _write_pdf(path, "\n".join(
        f"BT /F1 10 Tf {x} {700 - r * 20} Td ({value}) Tj ET"
        for r, row in enumerate([("Code", "Name"), ("A01", "Apple"), ("A02", "Pear")])
        for x, value in zip((60, 200), row)
    ))

    def fail(_self):
        raise OSError("Model unavailable")

    monkeypatch.setattr(StructuredPdfParser, "_get_converter", fail)
    result = parser_for(str(path)).parse(str(path))
    assert result.warnings
    assert result.blocks[0].kind == BlockKind.TABLE_HEADER
    assert result.blocks[-1].table_rows == (("A02", "Pear"),)


def test_new2_pptx_detects_borderless_table_of_grouped_text_shapes(tmp_path):
    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    group = slide.shapes.add_group_shape()
    for r, row in enumerate([("Code", "Name"), ("A01", "Apple"), ("A02", "Pear")]):
        for c, value in enumerate(row):
            box = group.shapes.add_textbox(Inches(1 + c * 2), Inches(2 + r), Inches(1), Inches(0.4))
            box.text = value
    path = tmp_path / "aligned.pptx"
    deck.save(path)
    blocks = parser_for(str(path)).parse(str(path)).blocks
    assert [block.kind for block in blocks] == [BlockKind.TABLE_HEADER, BlockKind.TABLE_ROW, BlockKind.TABLE_ROW]
    assert blocks[-1].table_rows == (("A02", "Pear"),)


def test_new2_xlsx_keeps_declared_blank_rows_and_empty_merge(tmp_path: Path):
    book = Workbook()
    sheet = book.active
    sheet.append(("Code", "Name"))
    sheet.append(("A01", "Apple"))
    sheet.add_table(Table(displayName="Fruit", ref="A1:B4"))
    sheet["D1"], sheet["E1"] = "Group", "Name"
    sheet["E2"], sheet["E3"] = "One", "Two"
    sheet.merge_cells("D2:D3")
    path = tmp_path / "ranges.xlsx"
    book.save(path)
    blocks = parser_for(str(path)).parse(str(path)).blocks
    headers = [b for b in blocks if b.kind == BlockKind.TABLE_HEADER]
    assert headers[0].table_rows == (("Code", "Name"),)
    rows = [b for b in blocks if b.location.index == headers[0].location.index and b.kind == BlockKind.TABLE_ROW]
    assert [b.location.row for b in rows] == [2, 3, 4]
    assert rows[-1].table_rows == ((None, None),)
    groups = [b for b in blocks if b.kind == BlockKind.TABLE_ROW_GROUP]
    assert groups[0].group_cells[0].range == "D2:D3"


@pytest.mark.parametrize("fmt", ["docx", "pptx", "pdf", "xlsx"])
def test_txt_groups_title_header_and_nested_row(fmt):
    child = _grid([["Key", "Value"], ["A01", "Apple"]])
    grid = _grid(
        [["Group", "Detail", "More", "System"], ["Fruit", None, None, "Backend"], ["Other", "Text", None, None]],
        title="Table 1",
    )
    grid.cells.append(GridCell(1, 1, 2, 3, children=[child, child]))
    indexes = iter(range(100))
    blocks = grid_blocks(grid, Location(sheet="Sheet1" if fmt == "xlsx" else None), (), indexes.__next__)
    output = _format_result(f"example.{fmt}", ParsedDocument(tuple(blocks), fmt))
    assert output.count("[table 1]") == 1
    assert (
        "Group: Fruit  |  Detail + More (병합 셀 B2:C2): [중첩 표 2 참조] [중첩 표 3 참조]"
        "  |  System: Backend"
    ) in output
    assert output.count("[중첩 표 2 참조]") == 1
    assert output.index("[중첩 표 2 참조]") < output.index("      [중첩 표 2] (parent_table_cell=B2:C2)")
    assert output.index("[table_title 1]") < output.index("[table_header 1]") < output.index("[table_row_group 1]")


@pytest.mark.parametrize("fmt", ["docx", "pptx", "pdf", "xlsx"])
def test_output_numbers_each_kind_independently(fmt):
    table = _grid([["Key", "Value"], ["A01", "Apple"]])
    indexes = iter((4, 9))
    location = Location(sheet="Sheet1") if fmt == "xlsx" else Location()

    def table_blocks():
        return grid_blocks(table, location, (), indexes.__next__, preserve_structure=True)

    result = ParsedDocument((
        Block(BlockKind.HEADING, Location(index=0), "Intro"),
        *table_blocks(),
        Block(BlockKind.PARAGRAPH, Location(index=5), "First paragraph"),
        Block(BlockKind.LIST_ITEM, Location(index=6), "List entry"),
        Block(BlockKind.PARAGRAPH, Location(index=7), "Second paragraph"),
        *table_blocks(),
        Block(BlockKind.HEADING, Location(index=10), "Next heading"),
    ), fmt)
    assert [(b.kind_number, b.table_number) for b in result.blocks] == [
        (1, None), (1, 1), (1, 1), (1, None), (1, None), (2, None), (2, 2), (2, 2), (2, None),
    ]
    output = _format_result(f"example.{fmt}", result)
    assert output.index("[table 1]") < output.index("[paragraph 2]") < output.index("[table 2]")
    assert "[heading 2] Location(index=10)" in output
    assert "[list_item 1] Location(index=6)" in output


def test_txt_nested_reference_keeps_column_order_in_vertical_merge():
    child = _grid([["Key", "Value"], ["A01", "Apple"]])
    grid = _grid([["No", "Step", "System"], ["2", None, "Backend"], ["3", None, "Frontend"]])
    grid.cells.append(GridCell(1, 1, 3, 2, "Review", children=[child]))
    output = _format_result("example.docx", ParsedDocument(tuple(_blocks(grid)), "docx"))
    assert "No: 2  |  Step (병합 셀 B2:B3): Review [중첩 표 2 참조]  |  System: Backend" in output
    assert "No: 3  |  System: Frontend" in output


def test_docling_word_title_with_custom_id_scopes_first_table(tmp_path):
    document = Document()
    style = document.styles["Title"]
    style.style_id = "a8"
    document.add_paragraph("Project\nProcess definition", style=style)
    table = document.add_table(rows=2, cols=2)
    for row, values in zip(table.rows, [("Item", "Description"), ("A01", "Example")]):
        for cell, value in zip(row.cells, values):
            cell.text = value
    path = tmp_path / "cover.docx"
    document.save(path)

    result = DoclingParser().parse(str(path))
    title, header = result.blocks[:2]
    assert title.kind == BlockKind.HEADING
    assert header.location.index == 1
    assert header.heading_path == (title.text,)
    output = _format_result(str(path), result)
    assert "[table 1]" in output
    assert "[table 2]" not in output


def test_docling_word_visual_heading_scopes_table(tmp_path):
    document = Document()
    title = document.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("Review procedure").font.size = Pt(24)
    note = document.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    note.add_run("Ordinary note").bold = True
    document.add_table(rows=1, cols=1).cell(0, 0).text = "Value"
    path = tmp_path / "visual.docx"
    document.save(path)
    heading, note, table = DoclingParser().parse(str(path)).blocks[:3]
    assert heading.kind == BlockKind.HEADING
    assert note.kind == BlockKind.PARAGRAPH
    assert table.heading_path == ("Review procedure",)


def test_docx_ignores_bold_boundaries_and_keeps_review_markup(tmp_path):
    path = tmp_path / "review.docx"
    doc = Document()
    paragraph = doc.add_paragraph("회원은 ")
    paragraph.add_run("14세 이상").bold = True
    paragraph.add_run("만 가입할 수 있다.")
    item = doc.add_paragraph("목록 ", style="List Bullet")
    item.add_run("중간").italic = True
    item.add_run(" 끝")
    for target in (doc.add_paragraph(), doc.add_table(rows=1, cols=1).cell(0, 0).paragraphs[0]):
        target.add_run("기존").font.strike = True
        target.add_run(" 값").font.strike = True
        target.add_run(" → ")
        target.add_run("새 값").font.color.rgb = RGBColor(255, 0, 0)
    doc.save(path)
    for parser in (DoclingParser(), parser_for(str(path))):
        blocks = parser.parse(str(path)).blocks
        assert [b.text for b in blocks[:3]] == [
            "회원은 14세 이상만 가입할 수 있다.", "목록 중간 끝", "~~기존 값~~ → <red>새 값</red>",
        ]
        assert blocks[1].kind == BlockKind.LIST_ITEM
        assert "~~기존 값~~ → <red>새 값</red>" in blocks[-1].text


def test_xlsx_sheet_heading_scopes_table(tmp_path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.merge_cells("A1:C1")
    sheet["A1"] = "Review procedure"
    sheet["A1"].font = Font(size=22)
    sheet["A1"].alignment = Alignment(horizontal="center")
    sheet["A4"], sheet["B4"] = "Code", "Label"
    sheet["A5"], sheet["B5"] = "A01", "Review"
    path = tmp_path / "visual.xlsx"
    workbook.save(path)
    for parser in (DoclingParser(), parser_for(str(path))):
        heading, table = parser.parse(str(path)).blocks[:2]
        assert heading.kind == BlockKind.HEADING
        assert table.kind == BlockKind.TABLE_HEADER
        assert table.heading_path == ("Review procedure",)


def test_pdf_visual_heading_uses_native_size_and_gap(tmp_path):
    path = tmp_path / "visual.pdf"
    _write_pdf(path, "\n".join(
        f"BT /F1 {size} Tf 60 {y} Td ({text}) Tj ET"
        for size, y, text in [
            (24, 720, "Review procedure"), (10, 680, "Ordinary body text."),
            (10, 650, "More ordinary body text."),
        ]
    ))
    doc = DoclingDocument(name="visual")
    doc.add_page(page_no=1, size=Size(width=595, height=842))
    for text, top, bottom, right in [
        ("Review procedure", 95, 135, 280), ("Ordinary body text.", 150, 168, 190),
        ("More ordinary body text.", 180, 200, 205),
    ]:
        doc.add_text(DocItemLabel.TEXT, text, prov=ProvenanceItem(
            page_no=1, bbox=BoundingBox(l=58, t=top, r=right, b=bottom), charspan=(0, len(text)),
        ))
    with PdfDocument(path) as pdf, closing(pdf[0]) as page:
        blocks = DoclingParser()._walk(str(path), "pdf", doc, (pdf, [page_chars(page)]), [])
    assert [block.kind for block in blocks] == [BlockKind.HEADING, BlockKind.PARAGRAPH, BlockKind.PARAGRAPH]
    assert blocks[1].heading_path == ("Review procedure",)


def test_txt_nested_reference_uses_table_order_instead_of_block_indexes():
    child = _grid([["Key", "Value"], ["A01", "Apple"]])
    grid = _grid([["No", "Step"], ["2", None]])
    grid.cells.append(GridCell(1, 1, 2, 2, children=[child]))
    blocks = grid_blocks(grid, Location(), (), iter((4, 9)).__next__)
    output = _format_result("example.docx", ParsedDocument(tuple(blocks), "docx"))
    assert "[table 1]" in output
    assert "[중첩 표 2 참조]" in output
    assert "[중첩 표 2]" in output


def test_camelot_recovers_uncaptioned_table_with_native_text(tmp_path: Path, monkeypatch):
    from transformers.image_utils import SizeDict

    path = tmp_path / "camelot.pdf"
    _write_pdf(path, "\n".join(
        f"BT /F1 10 Tf {x} {y} Td ({value}) Tj ET"
        for x, y, value in [
            (60, 705, "Report"), (60, 685, "Code"), (180, 685, "Name"),
            (60, 665, "A01"), (180, 665, "Apple"),
        ]
    ))
    calls = []

    def recognize(source, **kwargs):
        calls.append((source, kwargs))
        return [SimpleNamespace(
            cols=[(50, 160), (160, 270)], rows=[(720, 700), (700, 680), (680, 660)],
            parse={"spans": [(0, 0, 0, 1)]},
        )]

    monkeypatch.setattr("camelot.read_pdf", recognize)
    processor = SimpleNamespace(size=SizeDict(longest_edge=800))
    monkeypatch.setattr(
        "camelot.parsers.ml.MachineLearning._load_models",
        lambda _: SimpleNamespace(det_processor=processor, str_processor=processor),
    )
    doc = DoclingDocument(name="camelot")
    doc.add_page(page_no=1, size=Size(width=595, height=842))
    with PdfDocument(path) as source, closing(source[0]) as page:
        chars = page_chars(page)
        found = read_camelot_tables(str(path), 1, 842, chars)
        assert found[0].grid.cells[0].end_column == 2
        blocks = DoclingParser()._walk(str(path), "pdf", doc, (source, [chars]), [])
    assert all(kwargs["ocr"] is False and kwargs["flavor"] == "ml" for _, kwargs in calls)
    assert processor.size.shortest_edge == 800
    assert len(calls) == 2
    assert _texts(blocks, BlockKind.TABLE_TITLE) == ["Report"]
    assert _texts(blocks, BlockKind.TABLE_HEADER) == ["Code  |  Name"]
    assert _texts(blocks, BlockKind.TABLE_ROW) == ["Code: A01  |  Name: Apple"]


def test_pdf_ruled_repair_restores_merged_and_separate_cells(tmp_path: Path):
    path = tmp_path / "merged.pdf"
    _write_pdf(path, "\n".join([
        "0.8 w", "50 640 200 60 re S", "50 670 m 250 670 l S", "150 640 m 150 670 l S",
        "BT /F1 10 Tf 60 680 Td (Header) Tj ET",
        "BT /F1 10 Tf 60 650 Td (Left) Tj ET",
        "BT /F1 10 Tf 160 650 Td (Right) Tj ET",
    ]))
    with PdfDocument(path) as source, closing(source[0]) as page:
        chars = page_chars(page)
        box = (50, 142, 250, 202)
        split_header = _grid([["Header", None], ["Left", "Right"]])
        split_header.cells.append(GridCell(0, 1, 1, 2))
        collapsed_row = _grid([["Header"], ["Left Right"]])
        for grid in (split_header, collapsed_row):
            repaired = repair_pdf_grid(grid, page, box, chars)
            assert [(c.row, c.column, c.end_column, c.text) for c in repaired.cells] == [
                (0, 0, 2, "Header"), (1, 0, 1, "Left"), (1, 1, 2, "Right"),
            ]
