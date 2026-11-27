"""PPTX: 슬라이드의 도형을 직접 읽어 화면 순서(위 → 왼쪽 단 → 오른쪽 단)로 낸다.

읽는 것: 슬라이드 제목, 글상자, 목록, 그룹 도형, 표(병합·분리·겹쳐 놓은 중첩 표), SmartArt 글자.
읽지 않는 것: 숨긴 슬라이드·도형, 발표자 노트, 바닥글·날짜·번호, 그림, 차트.
"""

from collections import defaultdict
from statistics import median

from lxml import etree
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
from pptx.oxml.ns import qn
from pptx.util import Pt

from app.pipeline.models import Block, BlockKind, Location
from .docling_parser import _reading_order
from .base import FormatParser
from .pptx_tables import nest_overlapping, read_slide_table
from .table_grid import Grid, GridCell, grid_blocks, is_caption, structured_blocks

_TITLES = {PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE, PP_PLACEHOLDER.VERTICAL_TITLE}
_CHROME = {PP_PLACEHOLDER.FOOTER, PP_PLACEHOLDER.DATE, PP_PLACEHOLDER.SLIDE_NUMBER}
_SMARTART = "http://schemas.openxmlformats.org/drawingml/2006/diagram"


def _hidden(shape) -> bool:
    properties = next(shape._element.iter(qn("p:cNvPr")), None)
    return properties is not None and properties.get("hidden") in ("1", "true")


def _box(shape) -> tuple[float, float, float, float] | None:
    if None in (shape.left, shape.top, shape.width, shape.height):
        return None
    return shape.left, shape.top, shape.left + shape.width, shape.top + shape.height


def _to_slide(group, box):
    """그룹 안 좌표의 상자를 그룹 바깥 좌표로 바꾼다."""
    transform = group._element.find(f"{qn('p:grpSpPr')}/{qn('a:xfrm')}")
    if box is None or transform is None:
        return box
    off, ext, child_off, child_ext = (
        transform.find(qn(f"a:{tag}")) for tag in ("off", "ext", "chOff", "chExt")
    )
    if any(node is None for node in (off, ext, child_off, child_ext)):
        return box
    result = list(box)
    for axis, position, size in ((0, "x", "cx"), (1, "y", "cy")):
        scale = int(ext.get(size)) / (int(child_ext.get(size)) or 1)
        for i in (axis, axis + 2):
            result[i] = int(off.get(position)) + (box[i] - int(child_off.get(position))) * scale
    return tuple(result)


def _shapes(shapes, groups=()):
    """(도형, 슬라이드 좌표 상자). 그룹은 풀고 숨김·바닥글은 뺀다."""
    for shape in shapes:
        if _hidden(shape) or (shape.is_placeholder and shape.placeholder_format.type in _CHROME):
            continue
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _shapes(shape.shapes, (*groups, shape))
            continue
        box = _box(shape)
        for group in reversed(groups):
            box = _to_slide(group, box)
        yield shape, box


def _smartart_texts(shape, slide) -> list[str]:
    reference = next(shape._element.iter(f"{{{_SMARTART}}}relIds"), None)
    if reference is None:
        return []
    data = etree.fromstring(slide.part.related_part(reference.get(qn("r:dm"))).blob)
    texts = ("".join(t.text or "" for t in p.iter(qn("a:t"))).strip() for p in data.iter(qn("a:p")))
    return [text for text in texts if text]


def _paragraphs(shape) -> list[tuple[BlockKind, str]]:
    found = []
    for paragraph in shape.text_frame.paragraphs:
        text = paragraph.text.replace("\v", "\n").strip()
        if not text:
            continue
        properties = paragraph._p.pPr
        bullet = properties is not None and any(
            properties.find(qn(tag)) is not None for tag in ("a:buChar", "a:buAutoNum")
        )
        listed = bullet or paragraph.level > 0
        found.append((BlockKind.LIST_ITEM if listed else BlockKind.PARAGRAPH, text))
    return found


def _font(shape) -> tuple[float, bool]:
    """(가장 큰 글자 크기, 모두 굵은지)."""
    runs = [(p, r) for p in shape.text_frame.paragraphs for r in p.runs if r.text.strip()]
    sizes = [size.pt for p, r in runs if (size := r.font.size or p.font.size)]
    bold = bool(runs) and all(r.font.bold or (r.font.bold is None and p.font.bold) for p, r in runs)
    return max(sizes, default=0), bold


def _title(items):
    """제목 개체 틀, 없으면 맨 위에 홀로 있고 크거나 굵은 글상자."""
    texts = [(s, b) for s, b in items if s.has_text_frame and s.text_frame.text.strip()]
    for shape, _box_ in texts:
        if shape.is_placeholder and shape.placeholder_format.type in _TITLES:
            return shape
    placed = [(s, b) for s, b in items if b is not None and (s.has_table or s.has_text_frame and s.text_frame.text.strip())]
    if len(placed) < 2:
        return None
    shape, box = min(placed, key=lambda pair: pair[1][1])
    if shape.has_table or any(other[1] < box[3] for s, other in placed if s is not shape):
        return None
    size, bold = _font(shape)
    others = [found for s, _b in texts if s is not shape and (found := _font(s)[0])]
    return shape if bold or (others and size >= 1.2 * median(others)) else None


class SlideXmlParser(FormatParser):
    _grid_blocks = staticmethod(grid_blocks)
    name = "pptx-xml"
    extensions = ("pptx",)
    _package = "python-pptx"

    def _tables(self, number, items, title):
        tables = {
            shape.shape_id: (number, *read_slide_table(shape))
            for shape, _box in items if shape.has_table
        }
        return tables, nest_overlapping(tables)

    def _read(self, path: str, warnings: list[str]) -> list[Block]:
        blocks: list[Block] = []
        table_number = 0

        def next_index() -> int:
            nonlocal table_number
            table_number += 1
            return table_number - 1

        for number, slide in enumerate(Presentation(path).slides, start=1):
            if slide._element.get("show") in ("0", "false"):
                warnings.append(f"숨긴 슬라이드는 읽지 않음 (slide={number})")
                continue
            items = list(_shapes(slide.shapes))
            title = _title(items)
            tables, skipped = self._tables(number, items, title)
            heading: tuple[str, ...] = ()
            if title is not None:
                text = title.text_frame.text.replace("\v", "\n").strip()
                heading = (text,)
                blocks.append(Block(BlockKind.HEADING, Location(slide=number), text, heading_path=heading))

            rest = [(s, b) for s, b in items if title is None or s.shape_id != title.shape_id]
            # 내용이 없는 도형(배경 상자·선)은 단 나누기를 방해하므로 먼저 뺀다.
            content = []
            for shape, box in rest:
                if shape.shape_id in skipped:
                    continue
                if shape.shape_id in tables:
                    content.append((box, shape))
                elif shape.has_text_frame:
                    if shape.text_frame.text.strip():
                        content.append((box, shape))
                elif next(shape._element.iter(f"{{{_SMARTART}}}relIds"), None) is not None:
                    content.append((box, shape))
                elif shape.shape_type == MSO_SHAPE_TYPE.CHART or getattr(shape, "has_chart", False):
                    warnings.append(f"차트 안의 글자는 읽지 않음 (slide={number})")

            ordered = _reading_order([pair for pair in content if pair[0] is not None])
            for _box_, shape in [*ordered, *(pair for pair in content if pair[0] is None)]:
                location = Location(slide=number)
                if shape.shape_id in tables:
                    grid = tables[shape.shape_id][1]
                    blocks.extend(self._grid_blocks(grid, location, heading, next_index))
                    continue
                found = _paragraphs(shape) if shape.has_text_frame else [
                    (BlockKind.PARAGRAPH, text) for text in _smartart_texts(shape, slide)
                ]
                blocks.extend(Block(kind, location, text, heading_path=heading) for kind, text in found)
        return blocks


_ALIGNMENT_TOLERANCE = Pt(3)


def _text(shape):
    return shape.text_frame.text.replace("\v", "\n").strip() if shape.has_text_frame else ""


def _group_table(items):
    """Recognize a rectangular matrix of text shapes inside an explicit slide group."""
    rows = []
    for shape, box in sorted(items, key=lambda item: (item[1][1], item[1][0])):
        if not rows or abs(box[1] - rows[-1][0][1][1]) > _ALIGNMENT_TOLERANCE:
            rows.append([])
        rows[-1].append((shape, box))
    if len(rows) < 3:
        return None
    for row in rows:
        row.sort(key=lambda item: item[1][0])
    width = len(rows[0])
    if width < 2 or any(len(row) != width for row in rows):
        return None
    if any(abs(box[0] - rows[0][col][1][0]) > _ALIGNMENT_TOLERANCE
           for row in rows for col, (_, box) in enumerate(row)):
        return None
    if any(left[2] > right[0] for row in rows for (_, left), (_, right) in zip(row, row[1:])):
        return None
    if any(max(box[3] for _, box in upper) > min(box[1] for _, box in lower)
           for upper, lower in zip(rows, rows[1:])):
        return None
    cells = [
        GridCell(r, c, r + 1, c + 1, _text(shape))
        for r, row in enumerate(rows) for c, (shape, _) in enumerate(row)
    ]
    left, top = rows[0][0][1][:2]
    right = max(box[2] for _, box in items)
    bottom = max(box[3] for _, box in items)
    x = [left, *(box[0] for _, box in rows[0][1:]), right]
    y = [top, *(row[0][1][1] for row in rows[1:]), bottom]
    return rows[0][0][0].shape_id, Grid(len(rows), width, cells), {
        "x": x, "y": y, "box": (left, top, right, bottom), "space": "slide",
    }


class PptxParser(SlideXmlParser):
    """Read native tables and recover slide groups that represent borderless tables."""

    name = "new2-pptx"
    _grid_blocks = staticmethod(structured_blocks)

    def _tables(self, number, items, title):
        tables, groups, captions, skipped = {}, defaultdict(list), [], set()
        for shape, box in items:
            if shape.has_table:
                grid, geometry = read_slide_table(shape)
                if box and geometry and not shape.rotation:
                    for axis, start, end in (("x", box[0], box[2]), ("y", box[1], box[3])):
                        edges = geometry[axis]
                        extent = edges[-1] - edges[0]
                        if extent > 0:
                            geometry[axis] = [start + (v - edges[0]) * (end - start) / extent for v in edges]
                    geometry.update(box=box, space="slide")
                else:
                    geometry = {}
                tables[shape.shape_id] = (number, grid, geometry)
                continue
            if not box or shape is title or not (text := _text(shape)):
                continue
            if is_caption(text):
                captions.append((shape.shape_id, box, text))
            parent = shape._element.getparent()
            if not is_caption(text) and parent.tag.endswith("}grpSp") and not shape.rotation:
                groups[parent].append((shape, box))

        for group in groups.values():
            match = _group_table(group)
            if match is not None:
                anchor, grid, geometry = match
                tables[anchor] = (number, grid, geometry)
                skipped.update(shape.shape_id for shape, _ in group if shape.shape_id != anchor)

        skipped.update(nest_overlapping(tables))
        for shape_id, box, caption in captions:
            candidates = []
            for ref, (_, grid, geometry) in tables.items():
                if ref in skipped or not geometry or grid.title:
                    continue
                left, top, right, _ = geometry["box"]
                gap = top - box[3]
                if 0 <= gap <= Pt(20) and min(box[2], right) > max(box[0], left):
                    candidates.append((gap, ref, grid))
            if candidates:
                min(candidates)[2].title = caption
                skipped.add(shape_id)
        return tables, skipped
