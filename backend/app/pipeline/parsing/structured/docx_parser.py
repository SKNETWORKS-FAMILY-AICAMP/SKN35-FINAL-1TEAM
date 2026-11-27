"""DOCX: 원본 XML을 문서 순서대로 직접 읽는다 (AI 모델 없음).

읽는 것: 제목, 문단, 목록, 표(병합·중첩), 글상자(안의 표 포함), 각주·미주.
읽지 않는 것: 머리글·바닥글, 메모, 숨김·삭제 추적 글자, 그림.
shortcut: 자동 번호(1., 가.)의 번호 글자는 만들지 않는다. 번호 변경을 비교해야 하면 numbering.xml을 해석할 것.
"""

import re
from copy import deepcopy
from functools import partial
from itertools import count

from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import parse_xml
from docx.oxml.ns import qn

from app.pipeline.models import Block, BlockKind, Location
from .docx_tables import (
    _FALLBACK,
    _blocks,
    _caption_before,
    _paragraph,
    _style_id,
    _Styles,
    read_word_table,
    visually_prominent_title,
)
from .base import FormatParser
from .table_grid import grid_blocks, is_caption, structured_blocks
from docx.text.paragraph import Paragraph

_HEADING = re.compile(r"^(?:heading|제목)\s*(\d)$", re.IGNORECASE)


def _kind(paragraph, styles: _Styles) -> tuple[BlockKind, int]:
    """(블록 종류, 제목 단계). 문서 제목은 단계 0."""
    properties = paragraph.find(qn("w:pPr"))
    outline = None if properties is None else properties.find(qn("w:outlineLvl"))
    numbered = properties is not None and properties.find(qn("w:numPr")) is not None
    style = styles.get(_style_id(paragraph, f"{qn('w:pPr')}/{qn('w:pStyle')}"))
    while style is not None:    # 사용자 스타일은 바탕 스타일을 따라 올라간다.
        name = style.name or ""
        if name.lower() == "title":
            return BlockKind.HEADING, 0
        if match := _HEADING.match(name):
            return BlockKind.HEADING, int(match[1])
        own = style.element.find(qn("w:pPr"))
        if own is not None:
            if outline is None:
                outline = own.find(qn("w:outlineLvl"))
            numbered = numbered or own.find(qn("w:numPr")) is not None
        numbered = numbered or name.lower().startswith("list")
        style = style.base_style
    if outline is not None and (level := int(outline.get(qn("w:val"), 9))) < 9:
        return BlockKind.HEADING, level + 1
    return (BlockKind.LIST_ITEM if numbered else BlockKind.PARAGRAPH), 0


def _split_textboxes(paragraph) -> tuple[object, list]:
    """(글상자를 뺀 문단, 글상자 내용들). 같은 글상자의 구형 사본(Fallback)은 버린다."""
    if next(paragraph.iter(qn("w:txbxContent")), None) is None:
        return paragraph, []
    clone = deepcopy(paragraph)
    for fallback in list(clone.iter(_FALLBACK)):
        fallback.getparent().remove(fallback)
    boxes = [
        box for box in clone.iter(qn("w:txbxContent"))
        if not any(parent.tag == qn("w:txbxContent") for parent in box.iterancestors())
    ]
    for box in boxes:
        box.getparent().remove(box)
    return clone, boxes


class WordXmlParser(FormatParser):
    _grid_blocks = staticmethod(grid_blocks)
    _read_table = staticmethod(read_word_table)
    name = "docx-xml"
    extensions = ("docx",)
    _package = "python-docx"

    def _read(self, path: str, warnings: list[str]) -> list[Block]:
        document = Document(path)
        styles = _Styles(document)
        sequence = count()
        blocks: list[Block] = []
        headings: list[tuple[int, str]] = []    # (단계, 글자)

        def path_now() -> tuple[str, ...]:
            return tuple(text for _level, text in headings)

        def add(kind: BlockKind, text: str) -> None:
            blocks.append(Block(kind, Location(index=next(sequence)), text, heading_path=path_now()))

        def walk(container) -> None:
            elements = list(_blocks(container))
            caption = ""
            for position, element in enumerate(elements):
                if element.tag == qn("w:tbl"):
                    grid = self._read_table(element, styles)
                    grid.title = _caption_before(element, styles) or caption or grid.title
                    caption = ""
                    if grid.cells:
                        blocks.extend(self._grid_blocks(grid, Location(), path_now(), lambda: next(sequence)))
                    continue
                paragraph, boxes = _split_textboxes(element)
                text = _paragraph(paragraph, styles)[0]
                following = elements[position + 1] if position + 1 < len(elements) else None
                if text and following is not None and following.tag == qn("w:tbl") and (
                    is_caption(text) or text == _caption_before(following, styles)
                ):
                    caption = text      # 표 제목은 표와 함께 한 번만 낸다.
                elif text:
                    kind, level = _kind(element, styles)
                    if kind == BlockKind.PARAGRAPH and visually_prominent_title(
                        Paragraph(paragraph, document), document,
                    ):
                        kind, level = BlockKind.HEADING, 1
                    if kind == BlockKind.HEADING:
                        while headings and headings[-1][0] >= level:
                            headings.pop()
                        headings.append((level, text))
                    add(kind, text)
                for box in boxes:
                    walk(box)

        walk(document.element.body)
        headings.clear()
        for relation in (RT.FOOTNOTES, RT.ENDNOTES):
            for found in document.part.rels.values():
                if found.reltype != relation or found.is_external:
                    continue
                for note in parse_xml(found.target_part.blob):
                    if note.get(qn("w:type")) is None:      # 구분선 항목 제외
                        walk(note)
        return blocks


class DocxParser(WordXmlParser):
    """Read Word's recursive table XML, including borderless tables."""

    name = "new2-docx"
    _grid_blocks = staticmethod(structured_blocks)
    _read_table = staticmethod(partial(read_word_table, preserve_structure=True))
