"""PowerPoint 표를 원본에서 직접 읽고, 칸 위에 겹쳐 놓은 표를 중첩 표로 묶는다."""

from itertools import accumulate

from docling.backend.mspowerpoint_backend import MsPowerpointDocumentBackend
from docling_core.types.doc import TableCell, TableData
from pptx.oxml.ns import qn

from .table_grid import Grid, GridCell, encode_grid


def _cell(cell, row: int, column: int) -> GridCell:
    total = bold = 0
    lines = []
    for paragraph in cell.text_frame.paragraphs:
        lines.append(paragraph.text.replace("\v", "\n").strip())
        for run in paragraph.runs:
            length = len(run.text.strip())
            value = run.font.bold if run.font.bold is not None else paragraph.font.bold
            total += length
            bold += length if value else 0
    properties = cell._tc.find(qn("a:tcPr"))
    shaded = False
    if properties is not None:
        fill = properties.find(qn("a:solidFill"))
        if fill is not None:
            color = fill.find(qn("a:srgbClr"))
            shaded = color is None or color.get("val", "").upper() != "FFFFFF"
        shaded = shaded or properties.find(qn("a:gradFill")) is not None
    return GridCell(
        row, column, row + cell.span_height, column + cell.span_width,
        "\n".join(filter(None, lines)), bold == total if total else None, shaded,
    )


def read_slide_table(shape) -> tuple[Grid, dict]:
    table = shape.table
    cells = [
        _cell(cell, r, c)
        for r, row in enumerate(table.rows)
        for c, cell in enumerate(row.cells) if not cell.is_spanned
    ]
    grid = Grid(
        len(table.rows), len(table.columns), cells,
        header_hint=1 if table.first_row else None,
    )
    geometry = {}
    if None not in (shape.left, shape.top, shape.width, shape.height):
        parent = shape._element.getparent()
        geometry = {
            "x": list(accumulate((column.width for column in table.columns), initial=shape.left)),
            "y": list(accumulate((row.height for row in table.rows), initial=shape.top)),
            "box": [shape.left, shape.top, shape.left + shape.width, shape.top + shape.height],
            # 그룹 안 좌표는 그룹마다 기준이 다르므로 같은 부모끼리만 겹침을 비교한다.
            "space": parent.getroottree().getpath(parent),
        }
    return grid, geometry


class SlideTableBackend(MsPowerpointDocumentBackend):
    def _handle_tables(self, shape, parent_slide, slide_ind, doc, slide_size):
        if not shape.has_table:
            return
        grid, geometry = read_slide_table(shape)
        data = TableData(num_rows=1, num_cols=1, table_cells=[TableCell(
            text=encode_grid(grid, geometry),
            start_row_offset_idx=0, end_row_offset_idx=1,
            start_col_offset_idx=0, end_col_offset_idx=1,
        )])
        doc.add_table(
            data=data, parent=parent_slide, prov=self._generate_prov(shape, slide_ind, "", slide_size),
        )


def nest_overlapping(tables: dict[str, tuple[int, Grid, dict]]) -> set[str]:
    """{ref: (슬라이드, Grid, 좌표)}에서 칸 안에 완전히 들어간 표를 그 칸의 자식으로 옮긴다.

    자식이 된 표의 ref를 돌려준다.
    """
    nested = set()
    for ref, (slide, grid, geometry) in tables.items():
        if not geometry:
            continue
        left, top, right, bottom = geometry["box"]
        child_area = (right - left) * (bottom - top)
        if child_area <= 0:
            continue
        containers = []
        for other, (other_slide, parent, frame) in tables.items():
            if other == ref or other_slide != slide or not frame or frame["space"] != geometry["space"]:
                continue
            x, y = frame["x"], frame["y"]
            for cell in parent.cells:
                x0, x1 = x[cell.column], x[cell.end_column]
                y0, y1 = y[cell.row], y[cell.end_row]
                area = (x1 - x0) * (y1 - y0)
                if x0 <= left < right <= x1 and y0 <= top < bottom <= y1 and child_area < area:
                    containers.append((area, other, cell))
        containers.sort(key=lambda item: item[0])
        if containers and (len(containers) == 1 or containers[0][0] < containers[1][0]):
            containers[0][2].children.append(grid)
            nested.add(ref)
    return nested
