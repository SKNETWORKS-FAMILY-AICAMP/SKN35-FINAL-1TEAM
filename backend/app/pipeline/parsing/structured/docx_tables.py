"""Word 표를 원본 XML에서 직접 읽는다 (병합·중첩·서식 보존).

Docling은 본문 흐름만 맡고, 표 자리에는 Grid를 실은 자리표시 항목을 넣는다.
"""

from functools import cached_property
from itertools import groupby

from docling.backend.msword_backend import MsWordDocumentBackend
from docling_core.types.doc import TableCell, TableData
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

from .table_grid import Grid, GridCell, encode_grid, is_caption

_OFF = {"0", "false", "off", "none"}
_MATH_TEXT = "{http://schemas.openxmlformats.org/officeDocument/2006/math}t"
_FALLBACK = "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"


def _on(element) -> bool | None:
    """w:b, w:vanish 같은 켜짐/꺼짐 속성. 없으면 None."""
    if element is None:
        return None
    return str(element.get(qn("w:val"), "true")).lower() not in _OFF


def _children(element, tag: str):
    """바로 아래의 tag 요소. 내용 컨트롤(sdt)·변경 추적(ins) 껍질은 벗긴다."""
    for child in element:
        if child.tag == qn(tag):
            yield child
        elif child.tag in (qn("w:sdt"), qn("w:sdtContent"), qn("w:ins"), qn("w:customXml"), qn("w:smartTag")):
            yield from _children(child, tag)


def _blocks(element):
    for child in element:
        if child.tag in (qn("w:p"), qn("w:tbl")):
            yield child
        elif child.tag in (qn("w:sdt"), qn("w:sdtContent"), qn("w:ins"), qn("w:customXml")):
            yield from _blocks(child)


class _Styles:
    def __init__(self, document) -> None:
        self._by_id = {s.style_id: s for s in document.styles} if document is not None else {}

    def get(self, style_id):
        return self._by_id.get(style_id)

    def bold(self, style_id) -> bool | None:
        style = self.get(style_id)
        while style is not None:
            if style.type != 3 and style.font.bold is not None:     # 3 = 표 스타일
                return style.font.bold
            style = style.base_style
        return None


def _style_id(element, path: str) -> str | None:
    found = element.find(path)
    return None if found is None else found.get(qn("w:val"))


def _paragraph(paragraph, styles: _Styles) -> tuple[str, int, int]:
    """(글자, 전체 글자 수, 굵은 글자 수). 숨김 글자와 삭제 추적 글자는 읽지 않는다."""
    paragraph_bold = styles.bold(_style_id(paragraph, f"{qn('w:pPr')}/{qn('w:pStyle')}"))
    parts, total, bold = [], 0, 0
    strike = red = False

    def add(text):
        parts.append((strike, red, text))

    def walk(node) -> None:
        nonlocal total, bold, strike, red
        if node.tag in (_FALLBACK, qn("w:del"), qn("w:pPr"), qn("w:rPr")):
            return
        if node.tag == qn("w:r"):
            properties = node.find(qn("w:rPr"))
            if properties is not None and _on(properties.find(qn("w:vanish"))):
                return
            value = None if properties is None else _on(properties.find(qn("w:b")))
            if value is None and properties is not None:
                value = styles.bold(_style_id(properties, qn("w:rStyle")))
            value = paragraph_bold if value is None else value
            previous = strike, red
            strike = properties is not None and any(
                _on(properties.find(qn(tag))) for tag in ("w:strike", "w:dstrike")
            )
            color = None if properties is None else properties.find(qn("w:color"))
            red = color is not None and (color.get(qn("w:val")) or "").upper() == "FF0000"
            for child in node:
                if child.tag == qn("w:t") and child.text:
                    add(child.text)
                    length = len(child.text.strip())
                    total += length
                    bold += length if value else 0
                elif child.tag == qn("w:tab"):
                    add("\t")
                elif child.tag in (qn("w:br"), qn("w:cr")):
                    add("\n")
                elif child.tag == qn("w:noBreakHyphen"):
                    add("-")
                else:
                    walk(child)     # 글상자 등
            strike, red = previous
            return
        if node.tag == _MATH_TEXT and node.text:
            add(node.text)
        if node.tag == qn("w:p") and parts:
            add("\n")
        for child in node:
            walk(child)

    for child in paragraph:
        walk(child)
    rendered = []
    for (struck, colored), group in groupby(parts, key=lambda part: part[:2]):
        text = "".join(part[2] for part in group)
        if text.strip():
            if struck:
                text = f"~~{text}~~"
            if colored:
                text = f"<red>{text}</red>"
        rendered.append(text)
    return "".join(rendered).strip(), total, bold


def read_word_table(element, styles: _Styles, *, preserve_structure: bool = False) -> Grid:
    rows = list(_children(element, "w:tr"))
    cells: list[GridCell] = []
    open_cells: dict[int, GridCell] = {}     # 열 → 세로 병합이 열려 있는 칸
    columns = len(element.findall(f"{qn('w:tblGrid')}/{qn('w:gridCol')}"))
    header, leading = 0, True

    for row_number, row in enumerate(rows):
        properties = row.find(qn("w:trPr"))
        before = after = 0
        repeat = False
        if properties is not None:
            node = properties.find(qn("w:gridBefore"))
            before = 0 if node is None else int(node.get(qn("w:val"), 0))
            node = properties.find(qn("w:gridAfter"))
            after = 0 if node is None else int(node.get(qn("w:val"), 0))
            repeat = bool(_on(properties.find(qn("w:tblHeader"))))
        leading = leading and repeat
        header += leading

        column = before
        for tc in _children(row, "w:tc"):
            tc_properties = tc.find(qn("w:tcPr"))
            span, merge, shaded, horizontal = 1, None, False, None
            if tc_properties is not None:
                node = tc_properties.find(qn("w:gridSpan"))
                span = 1 if node is None else max(int(node.get(qn("w:val"), 1)), 1)
                node = tc_properties.find(qn("w:vMerge"))
                merge = None if node is None else node.get(qn("w:val"), "continue")
                node = tc_properties.find(qn("w:hMerge"))
                horizontal = None if node is None else node.get(qn("w:val"), "continue")
                node = tc_properties.find(qn("w:shd"))
                fill = "" if node is None else (node.get(qn("w:fill")) or "").upper()
                shaded = fill not in ("", "AUTO", "FFFFFF")

            texts, total, bold, tables = [], 0, 0, []
            for block in _blocks(tc):
                if block.tag == qn("w:tbl"):
                    child = read_word_table(block, styles, preserve_structure=preserve_structure)
                    caption = _caption_before(block, styles)
                    if not caption and texts and is_caption(texts[-1]):
                        caption = texts[-1]
                    child.title = caption or child.title
                    if child.title and texts and texts[-1] == child.title:
                        texts.pop()
                    tables.append(child)
                    continue
                text, length, bold_length = _paragraph(block, styles)
                if text:
                    texts.append(text)
                total += length
                bold += bold_length
            text = "\n".join(texts)

            origin = open_cells.get(column) if merge == "continue" else None
            if origin is not None and (origin.end_row != row_number or origin.end_column != column + span):
                origin = None
            if origin is None and horizontal == "continue" and cells and cells[-1].row == row_number:
                origin = cells[-1]
                origin.end_column = column + span
            elif origin is not None:
                origin.end_row = row_number + 1
            if origin is not None:
                if text and text != origin.text:
                    origin.text = "\n".join(filter(None, (origin.text, text)))
                origin.children.extend(tables)
            else:
                cell = GridCell(
                    row_number, column, row_number + 1, column + span, text,
                    bold == total if total else None, shaded, tables,
                )
                cells.append(cell)
                if merge == "restart":
                    open_cells[column] = cell
                else:
                    open_cells.pop(column, None)
            column += span
        columns = max(columns, column + after)

    title = ""
    if preserve_structure:
        caption = element.find(f"{qn('w:tblPr')}/{qn('w:tblCaption')}")
        if caption is not None:
            title = caption.get(qn("w:val"), "").strip()
    return Grid(len(rows), columns, cells, title=title, header_hint=header or None, hint_is_explicit=header > 0)


def _caption_before(element, styles: _Styles) -> str:
    """바로 앞 문단이 '캡션' 스타일이면 표 제목으로 본다."""
    previous = element.getprevious()
    if previous is None or previous.tag != qn("w:p"):
        return ""
    style = styles.get(_style_id(previous, f"{qn('w:pPr')}/{qn('w:pStyle')}"))
    name = "" if style is None else (style.name or "").lower()
    text = _paragraph(previous, styles)[0]
    if ("caption" not in name and "캡션" not in name) or not text:
        return ""
    # 그림 캡션을 표 제목으로 가져오지 않는다.
    return "" if text.startswith(("그림", "Figure")) and not is_caption(text) else text


class WordTableBackend(MsWordDocumentBackend):
    @cached_property
    def _word_styles(self):
        return _Styles(self.docx_obj)

    def _get_paragraph_elements(self, paragraph):
        if any(node.tag in {_MATH_TEXT, qn("w:txbxContent")} for node in paragraph._p.iter()):
            text = "".join(text for text, _, _ in super()._get_paragraph_elements(paragraph))
            return [(text, None, None)]
        return [(self._get_paragraph_text(paragraph), None, None)]

    def _get_paragraph_text(self, paragraph):
        if any(node.tag in {_MATH_TEXT, qn("w:txbxContent")} for node in paragraph._p.iter()):
            return super()._get_paragraph_text(paragraph)
        return _paragraph(paragraph._p, self._word_styles)[0]

    def _get_label_and_level(self, paragraph):
        # A built-in Word Title style can have a localized or opaque internal ID.
        for style in self._iter_style_chain(paragraph.style):
            if (style.name or "").strip().casefold() in {"title", "제목"}:
                return "Title", None
        label, level = super()._get_label_and_level(paragraph)
        if paragraph.style and paragraph.style.name == "Normal" and visually_prominent_title(paragraph, self.docx_obj):
            return "Heading", 1
        return label, level

    def _handle_tables(self, element, doc):
        styles = self._word_styles
        grid = read_word_table(element, styles)
        grid.title = _caption_before(element, styles)
        if not grid.cells:
            return []
        self._close_list_before_table()
        data = TableData(num_rows=1, num_cols=1, table_cells=[TableCell(
            text=encode_grid(grid),
            start_row_offset_idx=0, end_row_offset_idx=1,
            start_col_offset_idx=0, end_col_offset_idx=1,
        )])
        table = doc.add_table(
            data=data, parent=self.parents[self._get_level() - 1], content_layer=self.content_layer,
        )
        return [table.get_ref()]


def visually_prominent_title(paragraph, document) -> bool:
    """Require independent alignment and font-size evidence for an unstyled title."""
    text = paragraph.text.strip()
    element = paragraph._p
    if (
        not text or len(text) > 100 or text.endswith((".", "다."))
        or is_caption(text) or element.getparent() is not document.element.body
        or paragraph.alignment != WD_ALIGN_PARAGRAPH.CENTER
    ):
        return False
    body_size = document.styles.default(1)
    baseline = body_size.font.size.pt if body_size and body_size.font.size else 11
    styled = sum(
        len(run.text.strip()) for run in paragraph.runs
        if run.font.size is not None and run.font.size.pt >= max(16, baseline * 1.4)
    )
    return styled >= len(text.replace("\n", "")) * 0.8
