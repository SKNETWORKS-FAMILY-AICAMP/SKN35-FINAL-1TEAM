"""XLSX: openpyxl로 시트를 읽어 표 영역을 나눈다.

영역 분리·병합 처리는 xlsx_tables.py, 표 해석은 table_grid.py를 그대로 쓴다.
읽지 않는 것: 숨긴 시트·행·열, 메모, 그림·차트·도형의 글자.
"""

from dataclasses import replace
from functools import partial
from itertools import count

from app.pipeline.models import Block, BlockKind, Location
from .base import FormatParser
from .table_grid import grid_blocks, structured_blocks
from .xlsx_tables import read_workbook


class WorkbookParser(FormatParser):
    _grid_blocks = staticmethod(grid_blocks)
    name = "xlsx-openpyxl"
    extensions = ("xlsx",)
    _package = "openpyxl"
    _read_workbook = staticmethod(read_workbook)

    def _read(self, path: str, warnings: list[str]) -> list[Block]:
        parts, found = self._read_workbook(path)
        warnings.extend(found)
        blocks: list[Block] = []
        sequence = count()
        headings = {}
        for part in parts:
            location = Location(sheet=part.sheet, row=part.row)
            if part.grid is None:
                kind = BlockKind.HEADING if part.is_heading else BlockKind.PARAGRAPH
                if part.is_heading:
                    headings[part.sheet] = (part.text,)
                blocks.append(Block(kind, location, part.text, heading_path=headings.get(part.sheet, ())))
                continue
            table = self._grid_blocks(
                part.grid, replace(location, index=next(sequence)), headings.get(part.sheet, ()), sequence.__next__,
                prefix="열 ", loose_title=True,
                row_numbers=part.row_numbers, column_numbers=part.column_numbers,
            )
            if part.title_row is not None:
                table[0] = replace(table[0], location=replace(table[0].location, row=part.title_row))
            blocks.extend(table)
        return blocks


class XlsxParser(WorkbookParser):
    """Prefer declared worksheet tables and otherwise infer regions from cells."""

    name = "new2-xlsx"
    _grid_blocks = staticmethod(structured_blocks)
    _read_workbook = staticmethod(partial(read_workbook, preserve_structure=True))
