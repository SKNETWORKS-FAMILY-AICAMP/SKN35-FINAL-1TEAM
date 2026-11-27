from collections import Counter
from contextlib import closing
from itertools import count
from statistics import median

from pypdfium2 import PdfDocument, raw

from app.pipeline.models import Block, BlockKind, Location, ParsedDocument
from .base import ParseError
from .docling_parser import DoclingParser
from .pdf_tables import (
    PdfTable,
    _aligned_grid,
    _area,
    _coverage,
    _line_runs,
    _lines,
    boxes_overlap,
    center,
    contains,
    find_missing_pdf_tables,
    join_lines,
    page_chars,
    read_pdf_tables,
    repair_pdf_grid,
)
from .table_grid import data_pattern, is_caption, structured_blocks


def _bounds(chars):
    return (
        min(c["x0"] for c in chars), min(c["top"] for c in chars),
        max(c["x1"] for c in chars), max(c["bottom"] for c in chars),
    )


def _unclaimed_alignment(chars, claimed):
    """Find separate runs of aligned source text, without treating paragraphs as rows."""
    pending = []
    for line in _lines(chars):
        top = min(c["top"] for c in line)
        bottom = max(c["bottom"] for c in line)
        occupied = any(contains(box, center(c)) for box in claimed for c in line)
        eligible = not occupied and len(_line_runs(line)) >= 2
        if pending and (not eligible or top - pending[-1][1] > max(16, median(h for _, _, h in pending) * 2)):
            yield pending
            pending = []
        if eligible:
            pending.append((line, bottom, bottom - top))
    if pending:
        yield pending


def find_tables(page, chars, known, captions):
    found = find_missing_pdf_tables(page, chars, known, captions)
    claimed = [*known, *(table.box for table in found)]
    for segment in _unclaimed_alignment(chars, claimed):
        region = [char for line, _, _ in segment for char in line]
        grid = _aligned_grid(region)
        if grid is None or len(grid.cells) < grid.rows * grid.columns * 0.75:
            continue
        values = [cell.text for cell in grid.cells if cell.row > 0]
        # shortcut: two prose columns can share alignment; require compact or data-like cells.
        if not any(data_pattern(value) is not None for value in values) and median(map(len, values)) > 24:
            continue
        box = _bounds(region)
        if not any(boxes_overlap(box, previous) for previous in claimed):
            found.append(PdfTable(box, grid))
            claimed.append(box)
    return found


def repair_grid(grid, page, box, chars, model_tables):
    # A flat Docling grid can cover all text while still losing the table hierarchy.
    original = Counter(c["text"] for c in chars if contains(box, center(c)) and not c["text"].isspace())
    current = _coverage(grid, original)
    height = page.get_height()
    ruled = ()
    for path in page.get_objects(filter=[raw.FPDF_PAGEOBJ_PATH]):
        left, bottom, right, top = path.get_bounds()
        if max(right - left, top - bottom) >= 12 and (
            box[0] + 2 < left <= right < box[2] - 2
            and box[1] + 2 < height - top <= height - bottom < box[3] - 2
        ):
            ruled = read_pdf_tables(page, chars, box)
            break
    for candidate in ruled:
        if not any(cell.children for cell in candidate.grid.cells):
            continue
        intersection = (
            max(box[0], candidate.box[0]), max(box[1], candidate.box[1]),
            min(box[2], candidate.box[2]), min(box[3], candidate.box[3]),
        )
        if not boxes_overlap(box, candidate.box) or _area(intersection) < 0.75 * max(_area(box), _area(candidate.box)):
            continue
        missing, extra = _coverage(candidate.grid, original)
        if missing <= current[0] and extra <= current[1]:
            return candidate.grid
    return repair_pdf_grid(grid, page, box, chars, model_tables)


def _native_blocks(path, warnings):
    """Keep text and geometric tables available when layout models fail."""
    blocks, sequence = [], count()
    with PdfDocument(path) as pdf:
        for number in range(1, len(pdf) + 1):
            location = Location(page=number)
            with closing(pdf[number - 1]) as page:
                chars = page_chars(page)
                if not chars:
                    warnings.append(f"텍스트 레이어가 없는 페이지: {number}")
                    continue
                lines = []
                for line in _lines(chars):
                    box = _bounds(line)
                    lines.append((box, join_lines(line, box), line))
                captions = [box for box, text, _ in lines if is_caption(text)]
                tables = find_tables(page, chars, [], captions)
            items = []
            for box, text, line in lines:
                if is_caption(text):
                    targets = [
                        table for table in tables if not table.grid.title
                        and 0 <= table.box[1] - box[3] <= 24
                        and min(box[2], table.box[2]) > max(box[0], table.box[0])
                    ]
                    if targets:
                        min(targets, key=lambda table: table.box[1]).grid.title = text
                        continue
                kept = [c for c in line if not any(contains(table.box, center(c)) for table in tables)]
                if kept and (text := join_lines(kept, box)):
                    items.append((box, [Block(BlockKind.PARAGRAPH, location, text)]))
            # Allocate indices in reading order, including tables nested inside each entry.
            entries = [(box, found, None) for box, found in items]
            entries.extend((table.box, [], table.grid) for table in tables)
            for _, found, grid in sorted(entries, key=lambda entry: (entry[0][1], entry[0][0])):
                blocks.extend(found if grid is None else structured_blocks(grid, location, (), sequence.__next__))
    return blocks


class DoclingPdfParser(DoclingParser):
    name = "pdf-docling"
    extensions = ("pdf",)

    def parse(self, path: str) -> ParsedDocument:
        if not path.lower().endswith(".pdf"):
            raise ParseError(f"지원하지 않는 형식: {path}")
        return super().parse(path)


class PdfParser(DoclingPdfParser):
    """Use native PDF characters with Docling layout and geometric table recovery."""

    name = "new2-pdf"
    _grid_blocks = staticmethod(structured_blocks)
    _find_missing_pdf_tables = staticmethod(find_tables)
    _repair_pdf_grid = staticmethod(repair_grid)

    def _parse_flow(self, path, fmt, warnings):
        try:
            return super()._parse_flow(path, fmt, warnings)
        except Exception as exc:
            warnings.append(f"Docling PDF 분석 실패 ({type(exc).__name__}). PDF 원본 좌표로 복구했습니다.")
            return _native_blocks(path, warnings)
