"""Applies the agreed narrow QA rule and reviewer-status update to the casebook master/work views."""
from pathlib import Path
from openpyxl import load_workbook

HERE = Path(__file__).resolve().parent
BOOK = HERE / "영향팀_경계사례집_원본.xlsx"

# QA: only changed business rules, user behavior, API contracts, or acceptance criteria are impact.
# These are operational/configuration/document-only changes, or changes already covered by an earlier change.
NO = {
    "BC-TR-A-016-02", "BC-TR-A-042-02", "BC-TR-A-044-02", "BC-TR-A-062-02",
    "BC-TR-A-064-02", "BC-TR-A-066-02", "BC-TR-A-067-02", "BC-TR-B-026-01",
    "BC-TR-B-035-01", "BC-TR-A-018-02", "BC-TR-A-048-01", "BC-TR-B-037-01",
    "BC-CHG-002-01", "BC-CHG-004-01", "BC-CHG-B03-02", "BC-CHG-B04-01",
    "BC-CHG-B05-02", "BC-CHG-B16-01", "BC-CHG-B21-01",
}
# These were missed by the first review.
YES = {"BC-TR-A-052-01", "BC-TR-A-065-01", "BC-TR-B-059-01"}

def strip_prefix(text):
    text = str(text or "").strip()
    return text.replace("경계 사례 — ", "").replace("경계 — ", "")

def rationale(row, judgment):
    basis = strip_prefix(row["경계 근거"])
    change = str(row["변경 요약"])
    team = str(row["대상 팀"])
    doc = str(row["문서"])
    if judgment == "영향 있음":
        if team == "QA":
            return f"{basis}. 변경된 ‘{change}’는 {doc}의 업무 규칙·사용자 동작·API 계약 또는 합격 기준을 바꾸므로, QA는 관련 TC의 기대 결과를 추가하거나 갱신해야 한다."
        return f"{basis}. 다만 변경된 ‘{change}’는 {team}의 담당 산출물·구현·수행계획과 직접 연결되므로, 관련 기준을 반영하거나 수정해야 한다."
    return f"{basis}. 이 변경값은 {team}의 현재 담당 산출물·구현·검증 기준을 바꾸지 않거나 이미 선행 변경으로 반영되어 있어, 추가 조치가 필요하지 않다."

wb = load_workbook(BOOK)
for ws in wb.worksheets:
    header = {c.value: c.column for c in ws[1]}
    if "사례 ID" not in header:
        continue
    for r in range(2, ws.max_row + 1):
        case_id = ws.cell(r, header["사례 ID"]).value
        if not case_id:
            continue
        row = {name: ws.cell(r, col).value for name, col in header.items()}
        current = row.get("최종 판정")
        if case_id in NO:
            current = "영향 없음"
        elif case_id in YES:
            current = "영향 있음"
        ws.cell(r, header["최종 판정"]).value = current
        ws.cell(r, header["최종 판정 근거"]).value = rationale(row, current)
        ws.cell(r, header["검수 상태"]).value = "사람 검수 완료"
        # Preserve a precise reason category that can be filtered in Excel.
        if current == "영향 있음" and row.get("대상 팀") == "QA":
            ws.cell(r, header["판정 원칙"]).value = "업무 규칙·계약 변경에 따른 QA 검증"
        elif current == "영향 없음":
            ws.cell(r, header["판정 원칙"]).value = "담당 범위 비영향·기반영·운영 설정"

# Recalculate the summary sheet from the corrected master.
summary = wb["02a_최종판정_요약"]
master = wb["01_경계사례_마스터"]
mh = {c.value: c.column for c in master[1]}
rows = [{name: master.cell(r, col).value for name, col in mh.items()} for r in range(2, master.max_row + 1)]
groups = [("쇼핑몰 A · 가상 시나리오", "쇼핑몰 A", "가상 시나리오"),("구매 B · 가상 시나리오", "구매 B", "가상 시나리오"),("쇼핑몰 A · 실제 변경", "쇼핑몰 A", "실제 변경"),("구매 B · 실제 변경", "구매 B", "실제 변경")]
for i, (label, system, source) in enumerate(groups, start=2):
    xs = [x for x in rows if x["시스템"] == system and x["출처 유형"] == source]
    summary.cell(i, 2).value = sum(x["최종 판정"] == "영향 있음" for x in xs)
    summary.cell(i, 3).value = sum(x["최종 판정"] == "영향 없음" for x in xs)
    summary.cell(i, 4).value = len(xs)
all_yes = sum(x["최종 판정"] == "영향 있음" for x in rows)
summary.cell(6, 2).value = all_yes
summary.cell(6, 3).value = len(rows) - all_yes
summary.cell(6, 4).value = len(rows)
wb.save(BOOK)
print(f"{len(rows)}건 갱신: 영향 있음 {all_yes} / 영향 없음 {len(rows)-all_yes}")
