"""형식과 무관한 표 모델과 후처리 (헤더·제목 판정, 열 이름, 중첩 표 → Block).

형식별 모듈(docx/pptx/pdf/xlsx_tables.py)은 원본에서 Grid만 만들고,
"어디까지가 헤더인가, 행을 어떻게 문장으로 푸는가"는 여기 한 곳에서 정한다.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Callable, Collection, Mapping
from dataclasses import asdict, dataclass, field, replace
from functools import partial

from openpyxl.utils.cell import get_column_letter

from app.pipeline.models import Block, BlockKind, GroupCell, Location, TableCell


@dataclass
class GridCell:
    row: int            # 0부터, end_*는 미포함
    column: int
    end_row: int
    end_column: int
    text: str = ""
    bold: bool | None = None    # 글자가 없으면 None
    shaded: bool = False
    children: list["Grid"] = field(default_factory=list)    # 칸 안의 표


@dataclass
class Grid:
    rows: int
    columns: int
    cells: list[GridCell]
    title: str = ""
    header_hint: int | None = None  # 원본이 알려준 헤더 행 수. None = 정보 없음
    hint_is_explicit: bool = False  # True면 사용자가 직접 지정한 값 (Word '머리글 행 반복')


_CAPTION = re.compile(r"^\s*[\[<〈【(]?\s*(?:표|Table|TABLE)\s*[\dIVX]+(?:[-.]\d+)*(?:[\]>〉】).:]|\s|$)")
# 첫 칸이 이런 값이면 열 이름이 아니라 데이터일 가능성이 크다.
_DATA_PATTERNS = (
    re.compile(r"^[+-]?[\d,]+(?:\.\d+)?%?$"),                    # 숫자
    re.compile(r"^\d{4}[-./]\d{1,2}[-./]\d{1,2}.*$"),            # 날짜
    re.compile(r"^[A-Za-z]{1,6}[-_]?\d{1,6}(?:[-_.]\d+)*$"),     # ID (A01, FR-001)
    re.compile(r"^\d+[.)]\s"),                                   # 번호 목록
)
# 두 열짜리 '항목: 값' 표에서 첫 칸에 흔히 오는 이름
_KEY_LABELS = {
    "프로젝트명", "문서명", "문서번호", "문서버전", "문서상태", "작성자", "작성일", "작성팀",
    "최초작성일", "최종수정일", "검토자", "승인자", "발주처", "수행사", "공개범위", "버전", "담당자",
}
_GENERIC_HEADERS = {"내용", "값", "설명", "비고", "정보", "상세", "이름", "일자"} | _KEY_LABELS


def is_caption(text: str) -> bool:
    """'표 1. …' 같은 표 제목 줄인지. 본문 문장('표 1과 같이 …다.')은 제외한다."""
    text = text.strip()
    return len(text) <= 100 and not text.endswith("다.") and bool(_CAPTION.match(text))


def data_pattern(text: str) -> int | None:
    text = text.strip()
    return next((i for i, pattern in enumerate(_DATA_PATTERNS) if pattern.match(text)), None)


def _starting(grid: Grid, row: int) -> list[GridCell]:
    return [cell for cell in grid.cells if cell.row == row and (cell.text or cell.children)]


def _styled_rows(grid: Grid, attribute: str, first: int) -> int:
    """first 행부터 서식(굵게·음영)이 이어지는 행 수. 표 전체가 같은 서식이면 단서가 아니다."""
    count = 0
    for row in range(first, grid.rows):
        cells = _starting(grid, row)
        if not cells:
            if count and any(c.row < row < c.end_row for c in grid.cells):
                count += 1
                continue
            break
        enough = len(cells) >= 2 or grid.columns == 1 or cells[0].end_column - cells[0].column > 1 or count > 0
        if not enough or not all(getattr(cell, attribute) is True for cell in cells):
            break
        count += 1
    return count if first + count < grid.rows else 0


def _looks_headerless(grid: Grid, first: int) -> bool:
    if grid.rows - first < 2:
        return False
    row = sorted(_starting(grid, first), key=lambda c: c.column)
    if not row or row[0].column != 0:
        return False
    # 첫 열만 굵게/음영 = 왼쪽이 이름인 표
    column = [c for c in grid.cells if c.column == 0 and c.row >= first and c.text]
    others = [c for c in grid.cells if c.column > 0 and c.row >= first and c.text]
    for attribute in ("bold", "shaded"):
        if others and all(getattr(c, attribute) is True for c in column) and not any(
            getattr(c, attribute) is True for c in others
        ):
            return True
    if grid.columns == 2 and len(row) == 2:
        left, right = ("".join(c.text.split()) for c in row)
        if left in _KEY_LABELS and right not in _GENERIC_HEADERS:
            return True
    kind = data_pattern(row[0].text)
    if kind is None:
        return False
    below = [c for c in column if c.row > first]
    return bool(below) and sum(data_pattern(c.text) == kind for c in below) * 2 >= len(below)


def is_pair_table(grid: Grid, first: int = 0) -> bool:
    """'이름 | 값 | 이름 | 값' 처럼 한 행에 항목이 여러 쌍 놓인 머리글 없는 표인지."""
    if grid.columns < 4 or grid.columns % 2 or grid.hint_is_explicit:
        return False
    cells = [c for c in grid.cells if c.row >= first]
    if any(c.end_row - c.row > 1 or c.end_column - c.column > 1 or c.children for c in cells):
        return False
    top = {c.column: c.text for c in cells if c.row == first}
    names = [top.get(i, "") for i in range(0, grid.columns, 2)]
    values = [top.get(i, "") for i in range(1, grid.columns, 2)]
    # 첫 행의 이름 자리는 모두 글자이고, 값 자리에 데이터(ID·숫자·날짜·경로)가 있어야 한다.
    return all(names) and all(data_pattern(name) is None for name in names) and any(
        data_pattern(value) is not None or value.startswith("/") for value in values
    )


def title_rows(grid: Grid, *, loose: bool = False) -> int:
    """표 맨 위의 '제목 한 칸' 행 수. loose(XLSX)는 병합하지 않고 값 하나만 있어도 제목으로 본다."""
    count = 0
    while grid.columns > 1 and count < grid.rows - 1:
        cells = _starting(grid, count)
        if len(cells) != 1 or cells[0].children or cells[0].end_row != count + 1:
            break
        full = cells[0].column == 0 and cells[0].end_column == grid.columns
        if not (full or (loose and cells[0].column == 0)):
            break
        if len(_starting(grid, count + 1)) < 2 and not full:
            break
        count += 1
    return count


def header_row_count(grid: Grid, first: int = 0) -> int:
    """first(제목 다음 행)부터 헤더가 몇 행인지."""
    available = grid.rows - first
    if available <= 0 or is_pair_table(grid, first):
        return 0
    if available == 1:
        if grid.header_hint == 0 or any(c.children for c in _starting(grid, first)):
            return 0
        return 1

    styled = max(_styled_rows(grid, "bold", first), _styled_rows(grid, "shaded", first))
    if grid.hint_is_explicit and grid.header_hint:
        count = max(grid.header_hint - first, 1)
    elif styled:
        count = styled
    elif _looks_headerless(grid, first):
        return 0
    elif grid.header_hint is not None:
        count = grid.header_hint
    else:
        count = 1
    if count <= 0:
        return 0

    # 병합 구조로 헤더 확장: 세로 병합은 끝까지, 가로 병합 아래의 하위 제목 행까지.
    while first + count < grid.rows:
        end = first + count
        header = [c for c in grid.cells if first <= c.row < end and c.text]
        reach = max((c.end_row for c in header), default=end)
        if end < reach < grid.rows:
            count = reach - first
            continue
        groups = [c for c in header if 1 < c.end_column - c.column < grid.columns]
        below = _starting(grid, end)
        if (
            end + 1 < grid.rows and below and groups
            and all(
                any(g.column <= c.column and c.end_column <= g.end_column and g.end_row == end for g in groups)
                and not c.children and data_pattern(c.text) is None
                for c in below
            )
            and any(len({c.text for c in below if g.column <= c.column < g.end_column}) >= 2 for g in groups)
        ):
            count += 1
            continue
        break
    return count if count < available else 1


def first_row_columns(grid: Grid, row: int) -> tuple[tuple[int, int], ...]:
    """Use cell boundaries from the first table row only."""
    bounds = []
    cursor = 0
    for cell in sorted((cell for cell in grid.cells if cell.row == row), key=lambda cell: cell.column):
        if cell.end_column > cursor:
            bounds.append((max(cursor, cell.column), cell.end_column))
            cursor = cell.end_column
    return tuple(bounds)


def cell_labels(cell: TableCell, columns: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(columns[index] for index in cell.column_indexes)


def logical_rows(
    cells: list[TableCell], row_numbers: list[int], width: int,
) -> tuple[tuple[str | None, ...], ...]:
    values = {row: [[] for _ in range(width)] for row in row_numbers}
    for cell in cells:
        if cell.column_indexes and cell.value:
            values[cell.row][cell.column_indexes[0]].append(cell.value)
    return tuple(tuple("\n".join(parts) or None for parts in values[row]) for row in row_numbers)


def table_row_blocks(
    cells: list[TableCell],
    columns: tuple[str, ...],
    location: Location,
    heading_path: tuple[str, ...],
    header_rows: int,
    *,
    row_numbers: list[int],
    column_spans: tuple[tuple[int, int], ...],
    keep_rows: Collection[int] = (),
    references: Mapping[str, str] | None = None,
) -> list[Block]:
    references = references or {}
    by_row: dict[int, list[TableCell]] = defaultdict(list)
    for cell in cells:
        by_row[cell.row].append(cell)

    blocks = []
    start = 0
    while start < len(row_numbers):
        end = start
        last_row = row_numbers[start]
        lines = []
        merged = []
        group_cells = []
        while end < len(row_numbers) and row_numbers[end] <= last_row:
            active = by_row[row_numbers[end]]
            group_cells.extend(active)
            split = defaultdict(list)
            for cell in active:
                if len(cell.column_indexes) == 1:
                    split[cell.column_indexes[0]].append(cell)
            pairs = []
            rendered = set()
            for cell in active:
                last_row = max(last_row, cell.end_row)
                labels = cell_labels(cell, columns)
                if ":" in cell.range:
                    merged.append(GroupCell(cell.range, labels, cell.value))
                reference = references.get(cell.range)
                index = cell.column_indexes[0] if len(cell.column_indexes) == 1 else None
                if index is not None and len(split[index]) > 1:
                    if index in rendered:
                        continue
                    rendered.add(index)
                    parts = []
                    for part in split[index]:
                        value = part.value
                        if child := references.get(part.range):
                            value = " ".join(filter(None, (value, child)))
                        parts.append(value or "[빈 셀]")
                    pairs.append(f"{columns[index]}: [분리 셀] {' / '.join(parts)}")
                    continue
                value = " ".join(filter(None, (cell.value, reference)))
                if not value:
                    continue
                label = " + ".join(labels) or f"첫 행 범위 밖 ({cell.range})"
                if len(labels) > 1 or cell.row != cell.end_row:
                    label = f"{label} (병합 셀 {cell.range})"
                elif reference and labels:
                    span = f"병합 셀 {cell.range}" if ":" in cell.range else cell.range
                    label = f"{label} ({span})"
                pairs.append(f"{label}: {value}")
            if pairs:
                lines.append("  |  ".join(pairs))
            end += 1

        grouped = end > start + 1
        if lines or merged or row_numbers[start] in keep_rows:
            first_row = row_numbers[start]
            row_location = (
                replace(location, row=first_row, end_row=last_row if grouped else None)
                if location.sheet is not None else
                replace(location, table_row=first_row, table_end_row=last_row if grouped else None)
            )
            blocks.append(Block(
                BlockKind.TABLE_ROW_GROUP if grouped else BlockKind.TABLE_ROW,
                row_location, "\n".join(f"- {line}" if grouped else line for line in lines),
                heading_path=heading_path, group_cell=merged[0] if merged else None,
                context=", ".join(columns), table_columns=columns, table_header_rows=header_rows,
                table_rows=logical_rows(group_cells, row_numbers[start:end], len(columns)),
                group_cells=tuple(merged), table_cells=tuple(group_cells), table_column_spans=column_spans,
            ))
        start = end
    return blocks


def grid_blocks(
    grid: Grid,
    location: Location,
    heading_path: tuple[str, ...],
    next_index: Callable[[], int | None],
    *,
    prefix: str = "열",
    loose_title: bool = False,
    row_numbers: list[int] | None = None,
    column_numbers: list[int] | None = None,
    inherited_columns: tuple[str, ...] = (),
    inherited_spans: tuple[tuple[int, int], ...] = (),
    preserve_structure: bool = False,
) -> list[Block]:
    """Grid 하나(와 그 안의 표)를 읽기 순서의 Block 목록으로 만든다.

    row_numbers / column_numbers는 XLSX의 원본 행·열 번호(1부터)다. 없으면 표 안 순번을 쓴다.
    inherited_columns가 있으면 헤더 없이 이어지는 표(PDF 페이지 넘김)로 보고 그 이름을 쓴다.
    """
    sheet = location.sheet is not None
    row_numbers = row_numbers or list(range(1, grid.rows + 1))
    column_numbers = column_numbers or list(range(1, grid.columns + 1))
    if not sheet or preserve_structure or location.parent_table_index is not None or any(c.children for c in grid.cells):
        location = replace(location, index=next_index())

    if inherited_columns:
        titles, count = 0, 0
        columns, column_spans = inherited_columns, inherited_spans or first_row_columns(grid, 0)
    else:
        titles = title_rows(grid, loose=loose_title)
        if preserve_structure and grid.hint_is_explicit:
            titles = 0
            count = min(grid.rows, grid.header_hint or 0)
        else:
            count = header_row_count(grid, titles)
        column_spans = first_row_columns(grid, titles)
        labels = {c.column: " ".join(c.text.split()) for c in grid.cells if c.row == titles and c.text}
        names = [labels.get(left, f"{prefix}{index}") if count else f"{prefix}{index}"
                 for index, (left, _) in enumerate(column_spans, start=1)]
        duplicates = Counter(names)
        seen = Counter()
        columns = []
        for name in names:
            seen[name] += 1
            columns.append(f"{name}({seen[name]})" if duplicates[name] > 1 else name)
        columns = tuple(columns)
    data_start = titles + count
    references: dict[str, str] = {}

    def at(row: int) -> Location:
        return replace(location, row=row_numbers[row]) if sheet else location

    def children_of(cells) -> list[Block]:
        found = []
        for cell in sorted(cells, key=lambda c: (c.row, c.column)):
            for child in cell.children:
                child_location = replace(
                    location,
                    parent_table_index=location.index,
                    parent_table_cell=f"{get_column_letter(column_numbers[cell.column])}{row_numbers[cell.row]}",
                    parent_table_cell_end=(
                        f"{get_column_letter(column_numbers[cell.end_column - 1])}{row_numbers[cell.end_row - 1]}"
                    ),
                    table_row=None, table_end_row=None, row=None, end_row=None,
                )
                child_blocks = grid_blocks(
                    child, child_location, heading_path, next_index, prefix=prefix,
                    preserve_structure=preserve_structure,
                )
                if child_blocks and (index := child_blocks[0].location.index) is not None:
                    key = projected_cell(cell).range
                    reference = f"[중첩 표 {index + 1} 참조]"
                    references[key] = " ".join(filter(None, (references.get(key), reference)))
                found.extend(child_blocks)
        return found

    def projected_cell(cell: GridCell) -> TableCell:
        first = f"{get_column_letter(column_numbers[cell.column])}{row_numbers[cell.row]}"
        last = f"{get_column_letter(column_numbers[cell.end_column - 1])}{row_numbers[cell.end_row - 1]}"
        indexes = tuple(index for index, (left, right) in enumerate(column_spans)
                        if left < cell.end_column and cell.column < right)
        return TableCell(
            row_numbers[cell.row], row_numbers[cell.end_row - 1],
            first if first == last else f"{first}:{last}", indexes, cell.text,
        )

    def project(cells):
        return [projected_cell(cell) for cell in sorted(cells, key=lambda cell: (cell.row, cell.column))]

    def merge_info(cells):
        return tuple(GroupCell(cell.range, cell_labels(cell, columns), cell.value)
                     for cell in cells if ":" in cell.range)

    blocks: list[Block] = []
    shared = dict(
        heading_path=heading_path, table_columns=columns, table_column_spans=column_spans, table_header_rows=count,
    )
    if grid.title:
        blocks.append(Block(BlockKind.TABLE_TITLE, at(0), grid.title, **shared))
    for row in range(titles):
        cell = _starting(grid, row)[0]
        title_location = at(row)
        if preserve_structure and not sheet:
            title_location = replace(title_location, table_row=row + 1)
        title_cell = projected_cell(cell)
        details = dict(
            table_rows=logical_rows([title_cell], [row_numbers[row]], len(columns)),
            table_cells=(title_cell,), group_cells=merge_info([title_cell]),
        ) if preserve_structure else {}
        blocks.append(Block(BlockKind.TABLE_TITLE, title_location, cell.text, **shared, **details))

    if count:
        header_cells = [c for c in grid.cells if titles <= c.row < data_start]
        header_location = at(titles)
        if not sheet:
            header_location = replace(
                location, table_row=titles + 1, table_end_row=data_start if count > 1 else None,
            )
        header_data = project(header_cells)
        header_rows = logical_rows(header_data, row_numbers[titles:data_start], len(columns))
        header_text = "  |  ".join(columns)
        for row in header_rows[1:]:
            if any(row):
                header_text += "\n" + "  |  ".join(
                    f"{name}: {' / '.join(value.splitlines())}" for name, value in zip(columns, row) if value
                )
        for cell in header_data:
            if not cell.column_indexes and cell.value:
                header_text += f"\n첫 행 범위 밖 ({cell.range}): {cell.value}"
        children = children_of(header_cells)
        if sheet and count > 1:
            header_location = replace(header_location, end_row=row_numbers[data_start - 1])
        reference_header = None
        if references:
            by_column = {}
            for cell in header_data:
                if cell.range not in references:
                    continue
                label = " + ".join(cell_labels(cell, columns))
                index = cell.column_indexes[0] if cell.column_indexes else len(columns)
                by_column.setdefault(index, []).append(f"{label} ({cell.range}): {references[cell.range]}")
            reference_header = "  |  ".join(
                part for index, name in enumerate((*columns, ""))
                for part in by_column.get(index, [name]) if part
            )
            if "\n" in header_text:
                reference_header += "\n" + header_text.split("\n", 1)[1]
            references.clear()
        blocks.append(Block(
            BlockKind.TABLE_HEADER, header_location, header_text,
            table_rows=header_rows, table_cells=tuple(header_data), group_cells=merge_info(header_data),
            table_reference_text=reference_header, **shared,
        ))
        blocks.extend(children)

    data_cells = [cell for cell in grid.cells if cell.row >= data_start]
    projected = project(data_cells)
    nested = [cell for cell in data_cells if cell.children]
    numbers = row_numbers[data_start:]
    pairs = not inherited_columns and is_pair_table(grid, titles)

    def row_blocks(refs=None):
        return table_row_blocks(
            projected, columns, location, heading_path, count,
            row_numbers=numbers, column_spans=column_spans,
            keep_rows=numbers if preserve_structure else {row_numbers[cell.row] for cell in nested},
            references=refs,
        )

    display_positions = {}
    for block in row_blocks():
        first = block.location.row if sheet else block.location.table_row
        last = (block.location.end_row if sheet else block.location.table_end_row) or first
        if pairs:
            row = block.table_rows[0]
            text = "  |  ".join(
                f"{name or ''}: {value or ''}" for name, value in zip(row[::2], row[1::2]) if name or value
            )
            block = replace(block, text=text)
        inside = [cell for cell in nested if first <= row_numbers[cell.row] <= last]
        if inside:
            display_positions[block.location] = len(blocks)
            block = replace(block, kind=BlockKind.TABLE_ROW_GROUP)
        blocks.append(block)
        blocks.extend(children_of(inside))
    if references:
        for display in row_blocks(references):
            if (position := display_positions.get(display.location)) is not None:
                blocks[position] = replace(blocks[position], table_reference_text=display.text)
    return blocks


def grid_texts(grid: Grid) -> list[str]:
    texts = [grid.title]
    for cell in grid.cells:
        texts.append(cell.text)
        for child in cell.children:
            texts.extend(grid_texts(child))
    return [text for text in texts if text]


# Docling 변환 결과에 Grid를 실어 보내기 위한 직렬화 (전역 상태를 두지 않기 위함)
_MARK = "GRID\x1f"


def encode_grid(grid: Grid, extra: dict | None = None) -> str:
    return _MARK + json.dumps({"grid": asdict(grid), "extra": extra or {}}, ensure_ascii=False)


def decode_grid(text: str) -> tuple[Grid, dict] | None:
    if not text.startswith(_MARK):
        return None
    data = json.loads(text[len(_MARK):])

    def build(raw: dict) -> Grid:
        cells = [
            GridCell(**{**cell, "children": [build(child) for child in cell["children"]]})
            for cell in raw["cells"]
        ]
        return Grid(**{**raw, "cells": cells})

    return build(data["grid"]), data["extra"]


structured_blocks = partial(grid_blocks, preserve_structure=True)
