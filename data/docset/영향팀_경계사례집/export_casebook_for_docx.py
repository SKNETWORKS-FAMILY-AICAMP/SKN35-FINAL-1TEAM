"""Excel 최종 판정본을 Word 생성용 JSON으로 내보냅니다. 원본 문서세트는 수정하지 않습니다."""
from pathlib import Path
import json
from openpyxl import load_workbook

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "영향팀_경계사례집_원본.xlsx"
TARGET = HERE / "casebook_docx_data.json"

wb = load_workbook(SOURCE, data_only=True, read_only=True)
ws = wb["01_경계사례_마스터"]
headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
records = [dict(zip(headers, row)) for row in ws.iter_rows(min_row=2, values_only=True) if row[0]]
TARGET.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{len(records)}건을 {TARGET.name}에 저장했습니다.")
