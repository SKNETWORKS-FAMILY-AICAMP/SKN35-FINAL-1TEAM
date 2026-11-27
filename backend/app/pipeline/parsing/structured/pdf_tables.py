"""Docling PDF 표 변환과 원본 PDF 좌표 기반 보완."""

from collections import Counter
from collections.abc import Callable, Sequence
from contextlib import closing
from dataclasses import dataclass
from statistics import median

from pypdfium2 import raw

from .table_grid import Grid, GridCell, grid_texts

# 글자 사이 간격이 이보다 넓을 때만 띄어 쓴다. 보통의 띄어쓰기는 PDF의 공백 문자로 읽는다.
_X_TOLERANCE = 3.0

Box = tuple[float, float, float, float]     # (x0, top, x1, bottom), 페이지 왼쪽 위 기준

_TOLERANCE = 2.0


@dataclass
class PdfTable:
    box: Box
    grid: Grid


def center(item) -> tuple[float, float]:
    return (item["x0"] + item["x1"]) / 2, (item["top"] + item["bottom"]) / 2


def contains(box: Box, point: tuple[float, float]) -> bool:
    return box[0] <= point[0] <= box[2] and box[1] <= point[1] <= box[3]


def _coordinates(values) -> list[float]:
    result: list[float] = []
    for value in sorted(values):
        if not result or value - result[-1] > _TOLERANCE:
            result.append(value)
    return result


def _index(coordinates: list[float], value: float) -> int:
    return min(range(len(coordinates)), key=lambda i: abs(coordinates[i] - value))


def _narrow_gaps(text) -> set[int]:
    """pdfium이 자간을 보고 만들어 넣은 공백 중 낱말 띄어쓰기보다 좁은 것의 번호.

    Word의 '한글-숫자 간격 자동 조절' 틈을 공백으로 읽지 않기 위함이다.
    띄어쓰기 폭은 글꼴마다 달라서, 같은 페이지의 보통 폭(중앙값)과 비교한다.
    """
    ratios: dict[int, float] = {}
    for index in range(1, text.count_chars() - 1):
        if raw.FPDFText_GetUnicode(text, index) != 32 or raw.FPDFText_IsGenerated(text, index) != 1:
            continue
        left = text.get_charbox(index - 1, loose=True)
        right = text.get_charbox(index + 1, loose=True)
        size = left[3] - left[1]
        if size > 0 and abs(left[1] - right[1]) < 3 and 0 <= right[0] - left[2] < size * 0.6:
            ratios[index] = (right[0] - left[2]) / size
    if not ratios:
        return set()
    usual = median(ratios.values())
    return {index for index, ratio in ratios.items() if ratio < usual * 0.82}


def page_chars(page) -> list[dict]:
    """pypdfium2 페이지의 글자를 글자 좌표 형식(왼쪽 위 기준)으로 돌려준다."""
    height = page.get_height()
    with closing(page.get_textpage()) as text:
        return _page_chars(text, height)


def _page_chars(text, height: float) -> list[dict]:
    narrow = _narrow_gaps(text)
    chars: list[dict] = []
    for index in range(text.count_chars()):
        code = raw.FPDFText_GetUnicode(text, index)
        if code in (0, 10, 13) or 0xD800 <= code <= 0xDFFF:
            continue
        if index in narrow:
            continue
        # pdfium은 줄 끝의 하이픈을 0x02로 알려준다 (예: 'FR-' + 다음 줄 '003').
        value = "-" if code in (2, 0xFFFE) else chr(code)
        left, bottom, right, top = text.get_charbox(index, loose=True)
        if right <= left or top <= bottom:
            # 넓이가 없는 공백은 앞 글자 뒤에 붙여 낱말 경계만 남긴다.
            if not value.isspace() or not chars:
                continue
            previous = chars[-1]
            left, right = previous["x1"], previous["x1"] + 0.1
            top, bottom = height - previous["top"], height - previous["bottom"]
        chars.append({
            "text": value, "x0": left, "x1": right, "top": height - top, "bottom": height - bottom,
            "doctop": height - top, "upright": True, "size": top - bottom,
            "bold": raw.FPDFText_GetFontWeight(text, index) >= 700,
        })
    return chars


def _lines(chars):
    lines = []
    for char in sorted(chars, key=lambda c: c["bottom"]):
        if not lines or char["bottom"] - lines[-1][0] > 3:
            lines.append((char["bottom"], []))
        lines[-1][1].append(char)
    return [sorted(line, key=lambda c: c["x0"]) for _, line in lines]


def _line_words(line) -> list[dict]:
    found = []
    word = None
    for char in line:
        if char["text"].isspace():
            word = None
            continue
        if word is None or char["x0"] - word["x1"] > _X_TOLERANCE:
            word = dict(char)
            found.append(word)
        else:
            word["text"] += char["text"]
            word["x1"] = max(word["x1"], char["x1"])
            word["top"] = min(word["top"], char["top"])
            word["bottom"] = max(word["bottom"], char["bottom"])
    return found


def words(chars) -> list[dict]:
    return [word for line in _lines(chars) for word in _line_words(line)]


def cell_lines(chars) -> list[str]:
    return [" ".join(word["text"] for word in _line_words(line)) for line in _lines(chars)]


def join_lines(chars, box: Box) -> str:
    """칸 안에서 자동 줄바꿈된 줄을 한 줄로 잇는다.

    보통은 낱말 사이에서 넘어가므로 띄어 쓴다. 기호에서 끊겼거나,
    칸 끝까지 찬 줄 다음에 한 글자만 넘어간 경우(낱말 중간)는 붙여 쓴다.
    """
    lines = cell_lines(chars)
    if not lines:
        return ""
    right_edge = max((c["x1"] for c in chars), default=box[2])
    value = lines[0].strip()
    for previous, line in zip(lines, lines[1:]):
        current = line.strip()
        symbol = current.startswith(("-", ")", ".", ",")) or value.endswith(("-", "(", "_", "/"))
        size = max((c["size"] for c in chars), default=10)
        orphan = len(current) == 1 and not previous.endswith(" ") and box[2] - right_edge < size * 2
        # '입력·약' + '관 동의'처럼 가운뎃점으로 이은 긴 낱말은 글자 중간에서 넘어간다.
        head = current.split(" ", 1)[0]
        broken = "·" in value.rsplit(" ", 1)[-1] and len(head) == 1 and head not in "수및등후중시전내외"
        value += ("" if symbol or orphan or broken else " ") + current
    return value


def _is_bold(chars) -> bool | None:
    visible = [c for c in chars if not c["text"].isspace()]
    if not visible:
        return None
    return sum(c["bold"] for c in visible) * 2 > len(visible)


def _line_tables(page, crop: Box | None):
    """표 선의 연결 성분마다 닫힌 칸을 찾는다. 중첩 표의 선은 별도 성분이다."""
    import cv2

    width, height = page.get_size()
    left, top, right, bottom = crop or (0, 0, width, height)
    scale = min(2, 3500 / max(width, height))
    with closing(page.render(scale=scale, grayscale=True)) as bitmap:
        image = bitmap.to_numpy()
        if image.ndim == 3:
            image = image[:, :, 0]
        x = max(0, int(left * scale) - 6)
        y = max(0, int(top * scale) - 6)
        image = image[y:int(bottom * scale) + 7, x:int(right * scale) + 7]
        if not image.size:
            return []
        mask = cv2.threshold(image, 135, 255, cv2.THRESH_BINARY_INV)[1]
    horizontal = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (round(16 * scale), 1)))
    vertical = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, round(12 * scale))))
    lines = cv2.bitwise_or(horizontal, vertical)
    _, labels, stats, _ = cv2.connectedComponentsWithStats(lines)

    def to_pdf(x0, y0, w, h):
        return ((x + x0) / scale, (y + y0) / scale, (x + x0 + w) / scale, (y + y0 + h) / scale)

    found = []
    for label, (x0, y0, w, h, _) in enumerate(stats[1:], 1):
        if w < 20 * scale or h < 12 * scale:
            continue
        inside = (labels[y0:y0 + h, x0:x0 + w] != label).astype("uint8")
        _, _, holes, _ = cv2.connectedComponentsWithStats(inside, connectivity=4)
        cells = [
            to_pdf(x0 + cx, y0 + cy, cw, ch)
            for cx, cy, cw, ch, area in holes[1:]
            if cx > 0 and cy > 0 and cx + cw < w and cy + ch < h
            and cw > 4 * scale and ch > 4 * scale and area >= 0.95 * cw * ch
        ]
        if cells:
            found.append((to_pdf(x0, y0, w, h), cells))
    return found


def read_pdf_tables(page, chars: list[dict], crop: Box | None = None) -> list[PdfTable]:
    found = sorted(_line_tables(page, crop), key=lambda entry: _area(entry[0]))
    tables: list[PdfTable] = []
    for box, boxes in found:
        xs = _coordinates(v for cell in boxes for v in (cell[0], cell[2]))
        ys = _coordinates(v for cell in boxes for v in (cell[1], cell[3]))
        # 분리선 두께 때문에 생긴 가까운 경계를 하나로 취급한다.
        cells = []
        attached = []
        for cell in sorted(boxes, key=lambda b: (b[1], b[0])):
            row, column = _index(ys, cell[1]), _index(xs, cell[0])
            end_row, end_column = _index(ys, cell[3]), _index(xs, cell[2])
            if end_row <= row or end_column <= column:
                continue
            children = [table for table in tables if _inside(table.box, cell)]
            attached.extend(children)
            own = [c for c in chars if contains(cell, center(c))
                   and not any(contains(child.box, center(c)) for child in children)]
            cells.append(GridCell(
                row, column, end_row, end_column, join_lines(own, cell), _is_bold(own),
                children=[child.grid for child in children],
            ))
        if len(cells) >= 2 or attached:
            tables = [table for table in tables if table not in attached]
            tables.append(PdfTable(box, Grid(len(ys) - 1, len(xs) - 1, cells)))
    return tables


def _area(box: Box) -> float:
    return (box[2] - box[0]) * (box[3] - box[1])


def _inside(inner: Box, outer: Box) -> bool:
    return (outer[0] - 1 <= inner[0] and outer[1] - 1 <= inner[1]
            and inner[2] <= outer[2] + 1 and inner[3] <= outer[3] + 1
            and _area(inner) < 0.97 * _area(outer))


def box_contains(outer: Box, inner: Box) -> bool:
    return (outer[0] <= inner[0] and outer[1] <= inner[1]
            and inner[2] <= outer[2] and inner[3] <= outer[3])


def boxes_overlap(a: Box, b: Box) -> bool:
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def find_missing_pdf_tables(
    page, chars: list[dict], known: list[Box], captions: Sequence[Box] = (),
) -> list[PdfTable]:
    """Docling이 놓친 선 표와 캡션이 있는 정렬 표를 찾는다."""
    if not chars:
        return []
    height = page.get_height()
    # 표 후보가 이미 설명하는 벡터 도형만 있으면 페이지 영상 분석이 필요 없다.
    ruled = []
    for path in page.get_objects(filter=[raw.FPDF_PAGEOBJ_PATH]):
        left, bottom, right, top = path.get_bounds()
        bounds = left, height - top, right, height - bottom
        if max(right - left, top - bottom) >= 20 and not any(
            box_contains((x0 - 3, y0 - 3, x1 + 3, y1 + 3), bounds)
            for x0, y0, x1, y1 in known
        ):
            ruled = [
                table for table in read_pdf_tables(page, chars)
                if not any(boxes_overlap(table.box, box) for box in known)
                and table.grid.rows >= 2 and table.grid.columns >= 2
                and sum(bool(cell.text or cell.children) for cell in table.grid.cells) >= 3
            ]
            break
    found = list(ruled)
    for caption in captions:
        region = []
        previous = caption[3]
        below = [c for c in chars if c["top"] >= caption[3]]
        for line in _lines(below):
            top = min(c["top"] for c in line)
            if top - previous > 24 or len(_line_runs(line)) < 2:
                break
            region.extend(line)
            previous = max(c["bottom"] for c in line)
        if not region:
            continue
        box = (min(c["x0"] for c in region), min(c["top"] for c in region),
               max(c["x1"] for c in region), max(c["bottom"] for c in region))
        if any(boxes_overlap(box, other) for other in [*known, *(table.box for table in found)]):
            continue
        grid = _aligned_grid(region)
        if grid and len(grid.cells) == grid.rows * grid.columns:
            found.append(PdfTable(box, grid))
    return sorted(found, key=lambda table: (table.box[1], table.box[0]))


def grid_from_docling(table, page, chars: list[dict]) -> Grid:
    """Docling이 인식한 표를 Grid로. 굵기는 원본 PDF에서 읽는다."""
    cells, header_rows = [], set()
    for source in table.data.table_cells:
        if not (
            0 <= source.start_row_offset_idx < source.end_row_offset_idx <= table.data.num_rows
            and 0 <= source.start_col_offset_idx < source.end_col_offset_idx <= table.data.num_cols
        ):
            continue
        bold = None
        if source.bbox is not None:
            area = source.bbox.to_top_left_origin(page.get_height())
            box = (area.l, area.t, area.r, area.b)
            bold = _is_bold([c for c in chars if contains(box, center(c))])
        if source.column_header:
            header_rows.update(range(source.start_row_offset_idx, source.end_row_offset_idx))
        cells.append(GridCell(
            source.start_row_offset_idx, source.start_col_offset_idx,
            source.end_row_offset_idx, source.end_col_offset_idx,
            source.text.strip(), bold,
        ))
    hint = 0
    while hint in header_rows:
        hint += 1
    return Grid(table.data.num_rows, table.data.num_cols, cells, header_hint=hint or None)


def _line_runs(line):
    runs = []
    for word in _line_words(line):
        if not runs or word["x0"] - runs[-1][-1]["x1"] >= 9:
            runs.append([])
        runs[-1].append(word)
    return runs


def has_unclaimed_table_text(chars: list[dict], known: Sequence[Box]) -> bool:
    outside = [c for c in chars if not any(contains(box, center(c)) for box in known)]
    return sum(len(_line_runs(line)) >= 2 for line in _lines(outside)) >= 2


def _prepare_camelot_models() -> None:
    from camelot.parsers.ml import MachineLearning

    models = MachineLearning()._load_models()
    for processor in (models.det_processor, models.str_processor):
        size = processor.size
        # Camelot 2.2 보정은 dict에만 적용된다. Transformers 5는 SizeDict를 반환한다.
        if set(dict(size)) == {"longest_edge"}:
            size["shortest_edge"] = size["longest_edge"]


def read_camelot_tables(path: str, number: int, height: float, chars: list[dict]) -> list[PdfTable]:
    """Table Transformer의 구조에 PDFium의 원본 문자를 배치한다."""
    from camelot import read_pdf

    _prepare_camelot_models()
    raw_tables = read_pdf(
        path, pages=str(number), flavor="ml", ocr=False, backend="pdfium", use_fallback=False,
    )
    candidates = []
    for table in raw_tables:
        columns, rows = table.cols, table.rows
        if len(rows) < 2 or len(columns) < 2:
            continue
        spans = {}
        covered = set()
        for r0, c0, r1, c1 in (table.parse or {}).get("spans", ()):
            if not (0 <= r0 <= r1 < len(rows) and 0 <= c0 <= c1 < len(columns)):
                continue
            slots = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}
            if not covered.isdisjoint(slots):
                continue
            covered.update(slots)
            spans[r0, c0] = r1, c1
        boxes = []
        for row, (top, _) in enumerate(rows):
            for column, (left, _) in enumerate(columns):
                if (row, column) in covered and (row, column) not in spans:
                    continue
                last_row, last_column = spans.get((row, column), (row, column))
                box = (left, height - top, columns[last_column][1], height - rows[last_row][1])
                boxes.append((row, column, last_row + 1, last_column + 1, box))
        bounds = (columns[0][0], height - rows[0][0], columns[-1][1], height - rows[-1][1])
        candidates.append((bounds, len(rows), len(columns), boxes))

    found: list[PdfTable] = []
    for bounds, rows, columns, boxes in sorted(candidates, key=lambda item: _area(item[0])):
        page_chars = [char for char in chars if contains(bounds, center(char))]
        cells = []
        attached = []
        for row, column, end_row, end_column, box in boxes:
            children = [table for table in found if _inside(table.box, box)]
            attached.extend(children)
            own = [
                char for char in page_chars if contains(box, center(char))
                and not any(contains(child.box, center(char)) for child in children)
            ]
            cells.append(GridCell(
                row, column, end_row, end_column, join_lines(own, box), _is_bold(own),
                children=[child.grid for child in children],
            ))
        filled = [cell for cell in cells if cell.text or cell.children]
        if len({cell.row for cell in filled}) < 2 or len({cell.column for cell in filled}) < 2:
            continue
        found = [table for table in found if table not in attached]
        found.append(PdfTable(bounds, Grid(rows, columns, cells)))
    return found


def _aligned_grid(chars: list[dict]) -> Grid | None:
    """반복되는 열 시작점이 있는 무선 표의 칸 후보."""
    rows = [runs for line in _lines(chars) if (runs := _line_runs(line))]
    if len(rows) < 3:
        return None
    anchors = _coordinates(run[0]["x0"] for row in rows for run in row)
    used = [[_index(anchors, run[0]["x0"]) for run in row] for row in rows]
    counts = Counter(column for row in used for column in row)
    if len(anchors) < 2 or any(count < 2 for count in counts.values()):
        return None
    if sum(len(row) == len(anchors) for row in used) * 2 < len(rows):
        return None
    # 완전한 반복 정렬이 있어도 한 셀 안의 줄바꿈은 나뉠 수 있다.
    # 원문 누락 또는 일관되게 합쳐진 열을 복구하는 경우에 채택한다.
    return Grid(len(rows), len(anchors), [
        GridCell(r, c, r + 1, c + 1, " ".join(w["text"] for w in run), _is_bold(run))
        for r, (row, columns) in enumerate(zip(rows, used))
        for c, run in zip(columns, row)
    ])


def _coverage(grid: Grid, original: Counter) -> tuple[int, int]:
    extracted = Counter(c for text in grid_texts(grid) for c in text if not c.isspace())
    return sum((original - extracted).values()), sum((extracted - original).values())


def _spans(grid: Grid) -> set[tuple[int, int, int, int]]:
    return {(c.row, c.column, c.end_row, c.end_column) for c in grid.cells}


def repair_pdf_grid(
    grid: Grid, page, box: Box, chars: list[dict],
    model_tables: Callable[[], list[PdfTable]] | None = None,
) -> Grid:
    """원본에 구조 근거가 있는 경우에만 Docling의 표를 보완한다."""
    inside = [c for c in chars if contains(box, center(c))]
    original = Counter(c["text"] for c in inside if not c["text"].isspace())
    if not original:
        return grid
    current = _coverage(grid, original)
    aligned = _aligned_grid(inside)
    spans = _spans(grid)
    suspect = (
        current != (0, 0) or len(spans) != len(grid.cells)
        or grid.rows <= 1 or grid.columns <= 1
        or len(spans) != grid.rows * grid.columns
        or any(not c.text or len(c.text.splitlines()) > 1 for c in grid.cells)
        or (aligned is not None and aligned.columns != grid.columns)
    )
    if not suspect:
        return grid
    for table in read_pdf_tables(page, chars, box):
        if _area(table.box) < 0.75 * _area(box) or not contains(table.box, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)):
            continue
        candidate = table.grid
        score = _coverage(candidate, original)
        if score[0] <= current[0] and score[1] <= current[1] and (
            score != current or _spans(candidate) != spans or any(c.children for c in candidate.cells)
        ):
            if candidate.rows == grid.rows:
                candidate.header_hint = grid.header_hint
            return candidate
    if aligned:
        score = _coverage(aligned, original)
        complete_alignment = len(aligned.cells) == aligned.rows * aligned.columns
        if score[0] <= current[0] and score[1] <= current[1] and (score != current or (
            complete_alignment and grid.rows == aligned.rows and grid.columns < aligned.columns
        )):
            if aligned.rows == grid.rows:
                aligned.header_hint = grid.header_hint
            return aligned
    if model_tables:
        for table in model_tables():
            if not boxes_overlap(table.box, box):
                continue
            intersection = (max(table.box[0], box[0]), max(table.box[1], box[1]),
                            min(table.box[2], box[2]), min(table.box[3], box[3]))
            if _area(intersection) < 0.75 * max(_area(box), _area(table.box)):
                continue
            candidate = table.grid
            score = _coverage(candidate, original)
            structural_loss = (
                grid.rows <= 1 or grid.columns <= 1 or len(spans) != len(grid.cells)
                or (aligned is not None and grid.columns != aligned.columns == candidate.columns)
                or any(cell.children for cell in candidate.cells)
            )
            if score[0] <= current[0] and score[1] <= current[1] and (
                score != current or (structural_loss and _spans(candidate) != spans)
            ):
                if candidate.rows == grid.rows:
                    candidate.header_hint = grid.header_hint
                return candidate
    return grid
