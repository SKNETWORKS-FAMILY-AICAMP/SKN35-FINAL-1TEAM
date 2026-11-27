"""Excel 시트를 openpyxl로 직접 읽어 표 영역을 나눈다.

값이나 테두리가 이어진 칸을 한 영역으로 보고, 표 중간의 빈 행은 다시 이어 붙인다.
숨긴 시트·행·열은 읽지 않는다.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, time
from statistics import median

from openpyxl import load_workbook
from openpyxl.utils.cell import column_index_from_string, get_column_letter, range_boundaries

from .table_grid import Grid, GridCell, data_pattern, is_caption

_MAX_GAP = 2    # 이 줄 수까지의 빈 행은 표 안의 빈 행일 수 있다
_NUMBER_FORMAT = re.compile(r"^(?:#,##)?0(?:\.(?P<decimals>0+))?(?P<percent>%?)$")


@dataclass
class SheetPart:
    sheet: str
    row: int                            # 원본 첫 행 번호
    text: str = ""                      # 표가 아닌 홑 칸
    grid: Grid | None = None
    row_numbers: list[int] | None = None
    column_numbers: list[int] | None = None
    title_row: int | None = None        # 표 밖 제목의 원본 행 번호
    is_heading: bool = False


def _format(value, number_format: str) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == time() else value.isoformat(sep=" ")
    if isinstance(value, (date, time)):
        return value.isoformat()
    # 퍼센트와 소수 자릿수 지정 서식은 화면에 보이는 대로 읽는다.
    shown = _NUMBER_FORMAT.match((number_format or "").split(";")[0])
    if isinstance(value, (int, float)) and shown and (shown["decimals"] or shown["percent"]):
        percent = shown["percent"]
        return f"{value * (100 if percent else 1):.{len(shown['decimals'] or '')}f}{percent}"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.15g}"
    return str(value).strip()


def _hidden(sheet) -> tuple[set[int], set[int]]:
    rows = {number for number, d in sheet.row_dimensions.items() if d.hidden}
    columns = set()
    for letter, dimension in sheet.column_dimensions.items():
        if dimension.hidden:
            first = dimension.min or column_index_from_string(letter)
            columns.update(range(first, min(dimension.max or first, sheet.max_column) + 1))
    return rows, columns


def _bordered(cell) -> bool:
    border = cell.border
    return any(side is not None and side.style for side in (border.left, border.right, border.top, border.bottom))


def _shaded(cell) -> bool:
    fill = cell.fill
    if fill is None or fill.fill_type != "solid":
        return False
    color = fill.fgColor
    return not (color.type == "rgb" and str(color.rgb).upper().endswith("FFFFFF"))


def _components(points: set[tuple[int, int]]) -> list[tuple[int, int, int, int]]:
    boxes = []
    remaining = set(points)
    while remaining:
        stack = [remaining.pop()]
        top = bottom = stack[0][0]
        left = right = stack[0][1]
        while stack:
            r, c = stack.pop()
            top, bottom, left, right = min(top, r), max(bottom, r), min(left, c), max(right, c)
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if (r + dr, c + dc) in remaining:
                        remaining.remove((r + dr, c + dc))
                        stack.append((r + dr, c + dc))
        boxes.append((top, left, bottom, right))
    # 겹치는 영역은 하나로
    changed = True
    while changed:
        changed = False
        for i, a in enumerate(boxes):
            for j in range(i + 1, len(boxes)):
                b = boxes[j]
                if a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]:
                    boxes[i] = (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))
                    del boxes[j]
                    changed = True
                    break
            if changed:
                break
    return sorted(boxes)


def _continues(upper, lower, cells) -> bool:
    """빈 행 아래 영역이 위 표의 이어지는 데이터인지."""
    top, left, bottom, right = upper
    next_top, next_left, next_bottom, next_right = lower
    if not (0 < next_top - bottom - 1 <= _MAX_GAP and next_left == left and next_right <= right):
        return False
    if bottom == top or right == left:
        return False

    def row(number):
        return [cells[number, c] for c in range(left, right + 1) if (number, c) in cells and cells[number, c][0]]

    first = row(next_top)
    header = row(top)
    if len(first) < 2 or len(header) < 2 or any(v[1] or v[2] for v in first):
        # 아래 첫 행이 값 하나(제목)이거나 서식이 있으면(새 헤더) 별개의 표
        if len(first) < 2 or len(header) < 2:
            return False
        if all(v[1] for v in first) or all(v[2] for v in first):
            return False
    if all(v[1] or v[2] for v in header):
        return True
    key = cells.get((next_top, left))
    above = [cells[r, left][0] for r in range(top + 1, bottom + 1) if (r, left) in cells and cells[r, left][0]]
    if not key or not above:
        return False
    kind = data_pattern(key[0])
    return kind is not None and all(data_pattern(value) == kind for value in above)


def read_workbook(path: str, *, preserve_structure: bool = False) -> tuple[list[SheetPart], list[str]]:
    values = load_workbook(path, data_only=True)
    formulas = None
    parts: list[SheetPart] = []
    warnings: list[str] = []
    for sheet in values.worksheets:
        if sheet.sheet_state != "visible":
            continue
        hidden_rows, hidden_columns = _hidden(sheet)
        merges = []
        for area in sheet.merged_cells.ranges:
            merges.append((area.min_row, area.min_col, area.max_row, area.max_col))
        stored = {(c.row, c.column): c for row in sheet.iter_rows() for c in row}
        if any(r in hidden_rows or c in hidden_columns for (r, c), cell in stored.items() if cell.value is not None):
            warnings.append(f"시트 '{sheet.title}': 숨긴 행·열의 값은 읽지 않음")
        # 저장된 계산값이 없는 수식은 수식 문자열을 대신 쓴다.
        if formulas is None:
            formulas = load_workbook(path, data_only=False)
        source = formulas[sheet.title]

        # 숨긴 행·열을 뺀 화면상의 좌표
        tables = [(range_boundaries(table.ref), table.headerRowCount or 0)
                  for table in source.tables.values()] if preserve_structure else []
        used_rows = sorted({r for r, _ in stored} | {r for m in merges for r in (m[0], m[2])}
                           | {bounds[3] for bounds, _ in tables})
        used_columns = sorted({c for _, c in stored} | {c for m in merges for c in (m[1], m[3])}
                              | {bounds[2] for bounds, _ in tables})
        if not used_rows:
            continue
        row_numbers = [r for r in range(1, used_rows[-1] + 1) if r not in hidden_rows]
        column_numbers = [c for c in range(1, used_columns[-1] + 1) if c not in hidden_columns]
        row_of = {number: i for i, number in enumerate(row_numbers)}
        column_of = {number: i for i, number in enumerate(column_numbers)}

        cells: dict[tuple[int, int], tuple[str, bool, bool]] = {}    # (글자, 굵게, 음영)
        occupied: set[tuple[int, int]] = set()
        for (r, c), cell in stored.items():
            if r not in row_of or c not in column_of:
                continue
            text = _format(cell.value, cell.number_format)
            if cell.value is None:
                formula = source.cell(r, c).value
                if isinstance(formula, str) and formula.startswith("="):
                    text = formula
                    warnings.append(f"시트 '{sheet.title}' {get_column_letter(c)}{r}: 계산값이 없어 수식을 그대로 읽음")
            if text:
                cells[row_of[r], column_of[c]] = (text, bool(cell.font and cell.font.bold), _shaded(cell))
            if text or _bordered(cell):
                occupied.add((row_of[r], column_of[c]))

        declared = {}
        for (left, top, right, bottom), header_rows in tables:
            rows = [row_of[r] for r in range(top, bottom + 1) if r in row_of]
            columns = [column_of[c] for c in range(left, right + 1) if c in column_of]
            if rows and columns:
                header = sum(r in row_of for r in range(top, top + header_rows))
                declared[rows[0], columns[0], rows[-1], columns[-1]] = header
        if declared:
            occupied = {
                (r, c) for r, c in occupied
                if not any(top <= r <= bottom and left <= c <= right for top, left, bottom, right in declared)
            }

        spans: dict[tuple[int, int], tuple[int, int]] = {}
        for min_row, min_column, max_row, max_column in merges:
            rows = [row_of[r] for r in range(min_row, max_row + 1) if r in row_of]
            columns = [column_of[c] for c in range(min_column, max_column + 1) if c in column_of]
            if not rows or not columns:
                continue
            anchor = (rows[0], columns[0])
            if min_row not in row_of or min_column not in column_of:
                continue
            if anchor not in cells:
                if not preserve_structure:
                    continue
                cells[anchor] = ("", False, False)
            spans[anchor] = (rows[-1] + 1, columns[-1] + 1)
            if not any(top <= anchor[0] <= bottom and left <= anchor[1] <= right
                       for top, left, bottom, right in declared):
                occupied.update((r, c) for r in rows for c in columns)

        boxes = []
        for top, left, bottom, right in _components(occupied):
            held = [(r, c) for r, c in occupied if top <= r <= bottom and left <= c <= right and (r, c) in cells]
            if not held:
                continue
            ends = [spans.get(p, (p[0] + 1, p[1] + 1)) for p in held]
            boxes.append((
                min(r for r, _ in held), min(c for _, c in held),
                max(e[0] for e in ends) - 1, max(e[1] for e in ends) - 1,
            ))
        boxes.sort()

        merged: list[tuple[int, int, int, int]] = []
        for box in boxes:
            target = next((i for i, upper in enumerate(merged) if _continues(upper, box, cells)), None)
            if target is None:
                merged.append(box)
            else:
                upper = merged[target]
                merged[target] = (upper[0], upper[1], box[2], upper[3])

        merged = sorted(dict.fromkeys([*merged, *declared]))

        # 표 바로 위에 홀로 있는 칸은 그 표의 제목
        titles: dict[tuple[int, int, int, int], tuple[str, int]] = {}    # 표 → (제목, 화면 행)
        singles = [b for b in merged if b not in declared and sum((r, c) in cells for r in range(b[0], b[2] + 1) for c in range(b[1], b[3] + 1)) == 1]
        sizes = [float(cell.font.sz) for cell in stored.values() if cell.value is not None and cell.font.sz]
        baseline = median(sizes) if sizes else 11

        def is_heading(row, column):
            cell = sheet.cell(row_numbers[row], column_numbers[column])
            text = cells[row, column][0]
            if not text or len(text) > 100 or is_caption(text):
                return False
            if cell.style in {"Title", "Heading 1", "Heading 2", "Heading 3", "Heading 4"}:
                return True
            span = spans.get((row, column))
            return bool(
                span and span[1] > column + 1 and cell.alignment.horizontal in {"center", "centerContinuous"}
                and cell.font.sz and float(cell.font.sz) >= max(16, 1.35 * baseline)
                and not text.endswith(".")
            )

        for single in singles:
            if is_heading(single[0], single[1]):
                continue
            below = next((
                b for b in merged
                if b not in singles and b[3] > b[1] and 0 <= b[0] - single[2] - 1 <= 1 and b[1] == single[1]
            ), None)
            if below is not None and below not in titles:
                titles[below] = (cells[single[0], single[1]][0], single[0])

        used_titles = {(row, box[1]) for box, (_, row) in titles.items()}
        for box in merged:
            top, left, bottom, right = box
            if box in singles:
                text = cells[top, left][0]
                if (top, left) not in used_titles:
                    parts.append(SheetPart(sheet.title, row_numbers[top], text=text, is_heading=is_heading(top, left)))
                continue
            held = sorted((r, c) for r, c in cells if top <= r <= bottom and left <= c <= right)
            if box not in declared and len({r for r, _ in held}) == len(held) and all(
                spans.get(p, (0, p[1] + 1))[1] - p[1] > 1 for p in held
            ):
                # 가로 병합한 줄만 쌓인 영역은 표가 아니라 제목과 안내 문구다.
                parts.extend(
                    SheetPart(sheet.title, row_numbers[r], text=cells[r, c][0], is_heading=is_heading(r, c))
                    for r, c in held
                )
                continue
            grid_cells = []
            covered = set()
            for (r, c), (end_row, end_column) in spans.items():
                if top <= r <= bottom and left <= c <= right:
                    covered.update(
                        (i, j) for i in range(r, end_row) for j in range(c, end_column) if (i, j) != (r, c)
                    )
            for r in range(top, bottom + 1):
                for c in range(left, right + 1):
                    if (r, c) in covered:
                        continue
                    if (r, c) not in cells and not (r == top and (box in declared or (r, c) in occupied)):
                        continue
                    text, bold, shaded = cells.get((r, c), ("", False, False))
                    end_row, end_column = spans.get((r, c), (r + 1, c + 1))
                    grid_cells.append(GridCell(
                        r - top, c - left, min(end_row, bottom + 1) - top,
                        min(end_column, right + 1) - left, text, bold, shaded,
                    ))
            title, title_row = titles.get(box, ("", None))
            parts.append(SheetPart(
                sheet.title, row_numbers[top], grid=Grid(
                    bottom - top + 1, right - left + 1, grid_cells, title=title,
                    header_hint=declared.get(box), hint_is_explicit=box in declared,
                ),
                row_numbers=row_numbers[top:bottom + 1], column_numbers=column_numbers[left:right + 1],
                title_row=None if title_row is None else row_numbers[title_row],
            ))
    sheet_order = {name: index for index, name in enumerate(values.sheetnames)}
    return sorted(parts, key=lambda part: (sheet_order[part.sheet], part.row)), warnings
