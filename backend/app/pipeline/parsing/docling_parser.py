from pathlib import Path
from app.pipeline.parsing.base import ParseError
from app.pipeline.models import Location

SUPPORTED = ("pdf", "docs", "pptx", "xlsx")

# extension 구분
def _source_format(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")

    if ext not in  SUPPORTED:
        raise ParseError(f"지원하지 않는 형식: {ext}")
    return ext

def _to_location(item, fmt: str) -> Location:
    page = item.prov[0].page_no if item.prov else None
    if fmt == "pptx":
        return Location(slide=page)      # PPTX는 page_no가 슬라이드 번호일 가능성 (확인 필요)
    return Location(page=page)           # PDF, DOCX