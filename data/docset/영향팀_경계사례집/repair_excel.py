"""Rebuilds the casebook workbook without Excel Table metadata that can trigger a repair prompt."""
from pathlib import Path
from copy import copy
from openpyxl import load_workbook, Workbook

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "영향팀_경계사례집_원본.xlsx"
OUTPUT = HERE / "영향팀_경계사례집_원본_복구본.xlsx"

source = load_workbook(SOURCE, data_only=False)
target = Workbook()
target.remove(target.active)

for src in source.worksheets:
    dst = target.create_sheet(src.title)
    dst.sheet_view.showGridLines = src.sheet_view.showGridLines
    dst.freeze_panes = src.freeze_panes
    for row in src.iter_rows():
        for old in row:
            new = dst.cell(old.row, old.column, old.value)
            if old.has_style:
                new._style = copy(old._style)
            if old.number_format:
                new.number_format = old.number_format
            if old.alignment:
                new.alignment = copy(old.alignment)
            if old.font:
                new.font = copy(old.font)
            if old.fill:
                new.fill = copy(old.fill)
            if old.border:
                new.border = copy(old.border)
            if old.comment:
                new.comment = copy(old.comment)
    for letter, dim in src.column_dimensions.items():
        dst.column_dimensions[letter].width = dim.width
        dst.column_dimensions[letter].hidden = dim.hidden
    for index, dim in src.row_dimensions.items():
        dst.row_dimensions[index].height = dim.height
        dst.row_dimensions[index].hidden = dim.hidden
    for merged in src.merged_cells.ranges:
        dst.merge_cells(str(merged))
    # Keep filtering but intentionally omit Worksheet Tables (table*.xml), the suspected repair trigger.
    if src.max_row > 1 and src.max_column > 1:
        dst.auto_filter.ref = dst.dimensions

target.save(OUTPUT)
print(OUTPUT)
