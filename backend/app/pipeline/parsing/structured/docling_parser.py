"""Docling 기반 문서 파서 (DocumentParser Port의 구현체).

역할 분담
---------
    DOCX · PPTX : 본문 흐름은 Docling, 표는 원본 XML에서 직접 읽는다 (docx/pptx_tables.py)
    PDF         : Docling으로 본문과 표를 읽고, 구조가 어긋난 표만 원본 좌표로 보완한다.
    XLSX        : openpyxl로 직접 읽는다 (xlsx_tables.py)

표의 헤더·제목·행 그룹·중첩 판정은 형식과 무관하게 table_grid.py 한 곳에서 한다.

base.py 규칙 (반드시 지킴)
-------------------------
- 읽을 수 없으면 ParseError. 읽었지만 일부가 이상하면 예외가 아니라 warnings.
- 텍스트와 표만 읽는다. 서식과 문서 안 이미지는 버린다. (헤더 판정에만 서식을 참고한다)
- 정규화·마스킹·해시는 하지 않는다. 원문 그대로 돌려준다.
- 스캔 PDF는 제출 대상이 아니므로 OCR을 쓰지 않는다.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict, deque
from contextlib import closing
from dataclasses import dataclass, fields, replace
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from itertools import count
from pathlib import Path
from statistics import median

from pypdfium2 import PdfDocument
from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
    PowerpointFormatOption,
    WordFormatOption,
)
from docling_core.types.doc import (
    DocItemLabel,       # 문서 항목의 종류를 나타내는 라벨
    ListItem,           # 목록 항목
    SectionHeaderItem,  # 섹션 제목 항목
    TableItem,          # 표 항목
    TextItem,           # 일반 텍스트 항목
    TitleItem,          # 제목 항목
)
from docling_core.types.doc.common.content_layer import ContentLayer

from app.pipeline.models import Block, BlockKind, Location, ParsedDocument
from .base import ParseError
from .docx_tables import WordTableBackend
from .pdf_tables import (
    PdfTable,
    box_contains,
    boxes_overlap,
    center,
    contains,
    find_missing_pdf_tables,
    grid_from_docling,
    has_unclaimed_table_text,
    page_chars,
    read_camelot_tables,
    repair_pdf_grid,
    words,
)
from .pptx_headings import pptx_headings
from .pptx_tables import SlideTableBackend, nest_overlapping
from .table_grid import (
    Grid,
    data_pattern,
    decode_grid,
    grid_blocks,
    grid_texts,
    header_row_count,
    is_caption,
    title_rows,
)
from .xlsx_tables import read_workbook

logger = logging.getLogger(__name__)

# 이 파서가 처리하는 확장자 (점·대문자 없이). registry가 확장자 → 파서 매핑에 사용한다.
SUPPORTED = ("pdf", "docx", "pptx", "xlsx")

# 본문(BODY) 레이어만 읽는다.
#   FURNITURE  : 머리글/바닥글, 페이지 번호  → 노이즈
#   BACKGROUND : 워터마크                    → 노이즈
#   INVISIBLE  : 숨김 텍스트                 → 읽으면 안 됨 (프롬프트 인젝션 위험)
#   NOTES      : 발표자 노트, 교정 메모 등   → 본문이 아님
_BODY_ONLY = {ContentLayer.BODY}

# 텍스트 항목이어도 본문 문단으로 쓰지 않을 라벨.
# (레이어로 거르지 못한 경우를 대비한 이중 안전장치)
_SKIP_LABELS = {
    DocItemLabel.PAGE_HEADER,
    DocItemLabel.PAGE_FOOTER,
}


# ───────────────────────── 보조 함수 ─────────────────────────

def _source_format(path: str) -> str:
    """파일 확장자로 원본 형식을 판별한다. 지원하지 않으면 ParseError."""
    ext = Path(path).suffix.lower().lstrip(".")
    if ext not in SUPPORTED:
        raise ParseError(f"지원하지 않는 형식: {ext!r}")
    return ext


def _docling_version() -> str:
    """설치된 Docling 버전. 문서 버전 기록에 남긴다 (버전이 바뀌면 문단 분할이 달라질 수 있음)."""
    try:
        return _pkg_version("docling")
    except PackageNotFoundError:   # 설치 정보가 없는 특수 환경
        return "unknown"


def _update_heading_stack(stack: list[str], title_depth: int, level: int, text: str) -> list[str]:
    """섹션 제목을 만났을 때 제목 경로(스택)를 갱신해서 돌려준다.

    예) 스택 ["1장", "1.1절"] 에서 level=2 제목 "1.2절"을 만나면 → ["1장", "1.2절"]
        같은 단계 이상(깊은) 제목은 밀려나고, 상위 제목은 유지된다.

    title_depth : 문서 제목(Title)이 스택 맨 앞에 차지하는 칸 수 (0 또는 1).
                  문서 제목은 섹션 제목보다 항상 위 단계이므로 보존한다.
    level       : Docling의 섹션 제목 단계. 1이 최상위.
    """
    keep = title_depth + max(level, 1) - 1      # 유지할 상위 제목 개수
    return stack[:keep] + [text]


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _pdf_visual_headings(items, placed, chars, claimed):
    """Promote isolated, larger text outside tables when its layout supports a heading."""
    pages = defaultdict(list)
    repeated = defaultdict(set)
    for item in items:
        position = placed.get(item.self_ref)
        if position is None:
            continue
        page, box = position
        if isinstance(item, TableItem):
            pages[page].append((item, box, 0))
        elif isinstance(item, TextItem) and not any(boxes_overlap(box, area) for area in claimed[page]):
            sizes = [c["size"] for c in chars[page - 1] if not c["text"].isspace() and contains(box, center(c))]
            if sizes:
                pages[page].append((item, box, median(sizes)))
                repeated[_squash(item.text), round(box[0] / 12), round(box[1] / 12)].add(page)

    headings = set()
    for page, entries in pages.items():
        entries.sort(key=lambda entry: entry[1][1])
        sizes = [char["size"] for char in chars[page - 1] if not char["text"].isspace()]
        if not sizes:
            continue
        baseline = median(sizes)
        for (item, box, size), (_, below, _) in zip(entries, entries[1:]):
            if not isinstance(item, TextItem) or isinstance(item, (ListItem, TitleItem, SectionHeaderItem)):
                continue
            text = item.text.strip()
            if (
                item.label in _SKIP_LABELS or not text or len(text) > 100
                or text.endswith((".", "다.")) or is_caption(text)
                or size < 1.3 * baseline or below[1] - box[3] < 0.35 * size
                or min(box[2], below[2]) <= max(box[0], below[0])
                or len(repeated[_squash(text), round(box[0] / 12), round(box[1] / 12)]) > 1
            ):
                continue
            headings.add(item.self_ref)
    return headings


def _caption_text(table: TableItem, doc) -> str:
    return "\n".join(
        caption.text.strip()
        for ref in table.captions
        if isinstance(caption := ref.resolve(doc), TextItem)
        and caption.content_layer in _BODY_ONLY and caption.text.strip()
    )


def _item_box(item, doc) -> tuple[int, tuple[float, float, float, float]] | None:
    """PDF 항목의 (페이지, 왼쪽 위 기준 상자)."""
    if not getattr(item, "prov", None) or item.prov[0].page_no not in doc.pages:
        return None
    page = item.prov[0].page_no
    box = item.prov[0].bbox.to_top_left_origin(doc.pages[page].size.height)
    return page, (box.l, box.t, box.r, box.b)


def _reading_order(boxed: list) -> list:
    """[(상자, 항목)]을 화면 읽기 순서로 정렬한다.

    좌우로 갈라지면 왼쪽 단을 다 읽고 오른쪽으로, 아니면 맨 위 묶음부터 떼어 낸다.
    shortcut: 줄이 맞춰진 카드 격자도 단 단위로 읽는다. 그런 문서가 나오면 행 정렬을 먼저 확인할 것.
    """
    for start, end in ((0, 2), (1, 3)):     # 좌우 → 위아래
        ordered = sorted(boxed, key=lambda pair: pair[0][start])
        reach = float("-inf")
        for i, (box, _item) in enumerate(ordered):
            if i and box[start] >= reach - 0.5:
                return _reading_order(ordered[:i]) + _reading_order(ordered[i:])
            reach = max(reach, box[end])
    return boxed    # 서로 겹쳐 가를 수 없으면 원본 순서


def _order_slides(items: list, doc) -> list:
    """PPTX 항목을 도형을 만든 순서가 아니라 슬라이드별 화면 순서로 바꾼다."""
    pages: dict[int, list] = {}
    unplaced = []
    for item in items:
        placed = _item_box(item, doc)
        if placed:
            pages.setdefault(placed[0], []).append((placed[1], item))
        else:
            unplaced.append(item)
    return [item for page in sorted(pages) for _box, item in _reading_order(pages[page])] + unplaced


@dataclass
class _Previous:
    """페이지를 넘어 이어지는 표를 알아보기 위한 직전 PDF 표 정보."""
    page: int
    end: int                        # 이 표를 낸 직후의 블록 수
    box: tuple[float, float, float, float]
    columns: tuple[str, ...]
    column_spans: tuple[tuple[int, int], ...]
    grid_width: int
    header_styled: bool
    first_value_pattern: int | None


def _styled_first_row(grid: Grid) -> bool:
    cells = [c for c in grid.cells if c.row == 0 and c.text]
    return bool(cells) and (all(c.bold for c in cells) or all(c.shaded for c in cells))


def _continued_columns(previous: _Previous | None, page: int, box, grid: Grid, end: int) -> tuple[str, ...]:
    """앞 페이지 표가 머리글 없이 이어진 것이면 그 열 이름을 돌려준다."""
    if (
        previous is None or page != previous.page + 1 or end != previous.end
        or grid.columns != previous.grid_width
        or abs(box[0] - previous.box[0]) > 8 or abs(box[2] - previous.box[2]) > 8
    ):
        return ()
    first = sorted((c for c in grid.cells if c.row == 0 and c.text), key=lambda c: c.column)
    if not first or _styled_first_row(grid) or title_rows(grid):
        return ()
    if "  |  ".join(c.text for c in first) == "  |  ".join(dict.fromkeys(previous.columns)):
        return ()       # 머리글이 반복된 경우는 보통의 헤더로 처리
    same_kind = (
        previous.first_value_pattern is not None
        and data_pattern(first[0].text) == previous.first_value_pattern
    )
    if previous.header_styled or same_kind or grid.header_hint == 0:
        return previous.columns
    return ()


# ───────────────────────── 파서 본체 ─────────────────────────

class DoclingParser:
    """PDF / DOCX / PPTX / XLSX 를 ParsedDocument로 변환하는 파서.

    DocumentParser Protocol(base.py)의 규격을 따른다.
    """

    _find_missing_pdf_tables = staticmethod(find_missing_pdf_tables)
    _repair_pdf_grid = staticmethod(repair_pdf_grid)
    _grid_blocks = staticmethod(grid_blocks)

    name = "docling"
    extensions = SUPPORTED

    def __init__(self) -> None:
        # DocumentConverter는 생성/첫 사용 때 모델을 불러와 무겁다.
        # 그래서 처음 parse()를 부를 때 한 번만 만들고 계속 재사용한다.
        self._converter: DocumentConverter | None = None

    @property
    def version(self) -> str:
        """Docling 패키지 버전. 문서 버전 기록에 저장된다."""
        return _docling_version()

    def _get_converter(self) -> DocumentConverter:
        if self._converter is None:
            self._converter = DocumentConverter(format_options={
                InputFormat.DOCX: WordFormatOption(backend=WordTableBackend),
                InputFormat.PPTX: PowerpointFormatOption(backend=SlideTableBackend),
                InputFormat.PDF: PdfFormatOption(pipeline_options=PdfPipelineOptions(do_ocr=False)),
            })
        return self._converter

    def parse(self, path: str) -> ParsedDocument:
        """파일 하나를 ParsedDocument로 바꾼다.

        Raises:
            ParseError: 파일이 없거나, 지원하지 않는 형식이거나, 변환에 실패한 경우.
        """
        if not Path(path).is_file():
            raise ParseError(f"파일을 찾을 수 없음: {path}")
        fmt = _source_format(path)
        warnings: list[str] = []
        try:
            if fmt == "xlsx":
                blocks = self._parse_xlsx(path, warnings)
            else:
                blocks = self._parse_flow(path, fmt, warnings)
        except ParseError:
            raise
        except Exception as exc:
            raise ParseError(f"문서 변환 실패: {path} ({exc})") from exc

        # 블록이 하나도 없으면 스캔본/빈 문서일 가능성이 크다.
        if not blocks:
            warnings.append("추출된 텍스트가 없음 (스캔본 또는 빈 문서 의심)")
        return ParsedDocument(blocks=tuple(blocks), source_format=fmt, warnings=tuple(warnings))

    def _parse_xlsx(self, path: str, warnings: list[str]) -> list[Block]:
        parts, found = read_workbook(path)
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
            table = grid_blocks(
                part.grid, replace(location, index=next(sequence)), headings.get(part.sheet, ()), sequence.__next__,
                prefix="열 ", loose_title=True,
                row_numbers=part.row_numbers, column_numbers=part.column_numbers,
            )
            if part.title_row is not None:
                table[0] = replace(table[0], location=replace(table[0].location, row=part.title_row))
            blocks.extend(table)
        return blocks

    def _parse_flow(self, path: str, fmt: str, warnings: list[str]) -> list[Block]:
        """DOCX / PPTX / PDF : Docling의 읽기 순서를 따라가며 Block을 만든다."""
        result = self._get_converter().convert(path, raises_on_error=True)
        # 일부 페이지만 성공한 경우: 예외는 아니지만 결과가 불완전하므로 알린다.
        if result.status == ConversionStatus.PARTIAL_SUCCESS:
            warnings.append("일부 페이지/요소 변환 실패 (partial_success)")
        elif result.status != ConversionStatus.SUCCESS:
            raise ParseError(f"Docling 변환 상태 이상: {result.status}")
        doc = result.document
        if fmt != "pdf":
            return self._walk(path, fmt, doc, None, warnings)
        with PdfDocument(path) as pdf:
            chars = [page_chars(page) for page in pdf]
            empty = [str(number) for number, found in enumerate(chars, start=1) if not found]
            if empty:
                warnings.append(f"글자가 없는 페이지 (스캔 이미지 의심): {', '.join(empty)}")
            return self._walk(path, fmt, doc, (pdf, chars), warnings)

    def _walk(self, path: str, fmt: str, doc, source, warnings: list[str]) -> list[Block]:
        pdf, pdf_chars = source or (None, [])
        items = [item for item, _depth in doc.iterate_items(included_content_layers=_BODY_ONLY)]
        if fmt == "pptx":
            items = _order_slides(items, doc)
        blocks: list[Block] = []
        heading_stack: list[str] = []    # 현재 위치의 제목 경로
        title_depth = 0                  # 문서 제목(Title)이 스택에서 차지하는 칸 수
        sequence = count()               # DOCX는 항목 순번, PDF·PPTX는 표 번호

        def next_index() -> int:
            return next(sequence)

        # 원본에서 직접 읽은 표 (DOCX · PPTX)
        grids: dict[str, Grid] = {}
        slide_tables = {}
        for item in items:
            if isinstance(item, TableItem) and item.data.table_cells:
                decoded = decode_grid(item.data.table_cells[0].text)
                if decoded:
                    grids[item.self_ref] = decoded[0]
                    if fmt == "pptx" and item.prov:
                        slide_tables[item.self_ref] = (item.prov[0].page_no, *decoded)
        nested_refs = nest_overlapping(slide_tables)

        # 슬라이드 제목
        slide_headings: dict[str, str] = {}
        heading_by_slide: dict[int, str] = {}
        if fmt == "pptx":
            try:
                slide_headings = pptx_headings(path, doc)
            except Exception as exc:
                logger.debug("PPTX 제목 서식 확인 실패: %s", exc)
            for item in items:
                if slide_headings.get(item.self_ref) and item.prov:
                    heading_by_slide.setdefault(item.prov[0].page_no, slide_headings[item.self_ref])

        # 표 제목: Docling이 연결한 캡션, 또는 표 바로 앞의 '표 N …' 줄
        captions: dict[str, str] = {}
        skipped: set[str] = {
            ref.cref for table in doc.tables if table.content_layer in _BODY_ONLY for ref in table.captions
        }
        for previous, item in zip(items, items[1:]):
            if not isinstance(item, TableItem) or not isinstance(previous, TextItem):
                continue
            if isinstance(previous, ListItem) or previous.self_ref in slide_headings:
                continue
            grid = grids.get(item.self_ref)
            if grid is not None and grid.title and _squash(grid.title) == _squash(previous.text):
                skipped.add(previous.self_ref)
            elif is_caption(previous.text) and not item.captions and not (grid and grid.title):
                captions[item.self_ref] = previous.text.strip()
                skipped.add(previous.self_ref)

        previous_table: _Previous | None = None
        placed_items = {}
        recovered = {}
        pdf_headings = set()
        model_results: dict[int, list[PdfTable]] = {}
        model_failed = False

        def model_tables(page: int) -> list[PdfTable]:
            nonlocal model_failed
            if page not in model_results and not model_failed:
                try:
                    model_results[page] = read_camelot_tables(
                        path, page, doc.pages[page].size.height, pdf_chars[page - 1],
                    )
                except Exception as exc:
                    model_failed = True
                    warnings.append(f"PDF Camelot 표 구조 분석 실패 (page={page}): {exc}")
            return model_results.get(page, [])

        if pdf is not None:
            known = defaultdict(list)
            caption_boxes = defaultdict(list)
            placed_items = {item.self_ref: _item_box(item, doc) for item in items}
            for item in items:
                placed = placed_items[item.self_ref]
                if placed is None:
                    continue
                page, box = placed
                if isinstance(item, TableItem):
                    known[page].append(box)
                elif isinstance(item, TextItem) and item.self_ref not in skipped and is_caption(item.text):
                    caption_boxes[page].append(box)
            for page, chars in enumerate(pdf_chars, start=1):
                try:
                    with closing(pdf[page - 1]) as pdf_page:
                        tables = self._find_missing_pdf_tables(pdf_page, chars, known[page], caption_boxes[page])
                except Exception as exc:
                    warnings.append(f"PDF 누락 표 탐색 실패 (page={page}): {exc}")
                    tables = []
                claimed = [*known[page], *(table.box for table in tables)]
                if page in doc.pages and has_unclaimed_table_text(chars, claimed):
                    for table in model_tables(page):
                        if not any(boxes_overlap(table.box, box) for box in claimed):
                            tables.append(table)
                            claimed.append(table.box)
                if tables:
                    recovered[page] = sorted(tables, key=lambda table: (table.box[1], table.box[0]))
            for page, tables in recovered.items():
                known[page].extend(table.box for table in tables)
            pdf_headings = _pdf_visual_headings(items, placed_items, pdf_chars, known)
        pending = deque((page, table) for page, tables in recovered.items() for table in tables)

        def emit_pdf_grid(grid: Grid, page: int, box, heading: tuple[str, ...]) -> None:
            nonlocal previous_table
            inherited = _continued_columns(previous_table, page, box, grid, len(blocks))
            table = self._grid_blocks(
                grid, Location(page=page), heading, next_index, inherited_columns=inherited,
                inherited_spans=previous_table.column_spans if inherited else (),
            )
            blocks.extend(table)
            if not table:
                return
            data_start = 0
            if not inherited:
                titles = title_rows(grid)
                data_start = titles + header_row_count(grid, titles)
            first_data = next(
                (c.text for c in grid.cells if c.column == 0 and c.row >= data_start and c.text), "",
            )
            previous_table = _Previous(
                page, len(blocks), box, tuple(inherited or table[0].table_columns),
                table[0].table_column_spans, grid.columns,
                previous_table.header_styled if inherited else _styled_first_row(grid),
                data_pattern(first_data),
            )

        slide_number = None
        for item in items:
            if item.self_ref in skipped or item.self_ref in nested_refs:
                continue
            page = item.prov[0].page_no if getattr(item, "prov", None) else None

            if fmt == "pptx" and page is not None and page != slide_number:
                slide_number = page
                heading_stack, title_depth = [], 0
                if heading := heading_by_slide.get(page):
                    # 슬라이드 제목은 도형 순서와 무관하게 그 슬라이드의 맨 앞에 낸다.
                    heading_stack, title_depth = [heading], 1
                    blocks.append(Block(BlockKind.HEADING, Location(slide=page), heading, heading_path=(heading,)))
            if item.self_ref in slide_headings:
                continue
            path_now = tuple(heading_stack)           # 이 블록이 속한 제목 경로 (불변 tuple)

            placed = placed_items.get(item.self_ref)
            if placed:
                number, box = placed
                if isinstance(item, TextItem) and is_caption(item.text) and pending:
                    target_page, target = pending[0]
                    if target_page == number and 0 <= target.box[1] - box[3] <= 24:
                        if min(box[2], target.box[2]) > max(box[0], target.box[0]):
                            target.grid.title = item.text.strip()
                            continue
                while pending and (pending[0][0], pending[0][1].box[1]) <= (number, box[1]):
                    recovered_page, table = pending.popleft()
                    emit_pdf_grid(table.grid, recovered_page, table.box, path_now)
                if isinstance(item, TextItem) and (content := _squash(item.text)) and any(
                    box_contains(table.box, box)
                    and content in _squash(" ".join(grid_texts(table.grid)))
                    for table in recovered.get(number, ())
                ):
                    continue

            def at(page: int | None = page) -> Location:
                if fmt == "docx":
                    return Location(index=next_index())     # 블록을 낼 때만 순번을 쓴다
                if page is None:
                    return Location()
                return Location(slide=page) if fmt == "pptx" else Location(page=page)

            # ── 표 ──
            if isinstance(item, TableItem):
                caption = captions.get(item.self_ref, "")
                if item.self_ref in grids:
                    grid = grids[item.self_ref]
                    grid.title = grid.title or caption
                    base = Location(slide=page) if fmt == "pptx" and page is not None else Location()
                    blocks.extend(grid_blocks(grid, base, path_now, next_index))
                elif placed:
                    number, box = placed
                    chars = pdf_chars[number - 1]
                    with closing(pdf[number - 1]) as pdf_page:
                        grid = grid_from_docling(item, pdf_page, chars)
                        try:
                            grid = self._repair_pdf_grid(grid, pdf_page, box, chars, lambda: model_tables(number))
                        except Exception as exc:
                            warnings.append(f"PDF 표 구조 보완 실패 (page={number}): {exc}")
                    grid.title = _caption_text(item, doc) or caption
                    emit_pdf_grid(grid, number, box, path_now)
                    # 표 인식이 빠뜨린 글자는 버리지 않고 따로 남긴다.
                    kept = _squash("".join(grid_texts(grid)))
                    lost = [
                        word["text"] for word in words(chars)
                        if contains(box, center(word)) and _squash(word["text"]) not in kept
                    ]
                    if lost:
                        warnings.append(f"표 인식에서 빠진 글자를 별도 문단으로 남김 (page={number}): {len(lost)}개")
                        blocks.append(Block(
                            BlockKind.PARAGRAPH, Location(page=number), " ".join(lost), heading_path=path_now,
                        ))
                continue

            if not isinstance(item, TextItem) or not item.text.strip():
                continue        # 그림(PictureItem) 등은 의도적으로 무시한다.

            # ── 문서 제목 ── (TitleItem은 TextItem의 하위 클래스이므로 먼저 검사)
            inferred_heading = item.self_ref in pdf_headings
            if isinstance(item, TitleItem) or item.label == DocItemLabel.TITLE or (inferred_heading and not blocks):
                heading_stack, title_depth = [item.text], 1
                blocks.append(Block(BlockKind.HEADING, at(), item.text, heading_path=tuple(heading_stack)))
            # ── 섹션 제목 ──
            elif isinstance(item, SectionHeaderItem) or inferred_heading:
                level = item.level if isinstance(item, SectionHeaderItem) else 1
                heading_stack = _update_heading_stack(heading_stack, title_depth, level, item.text)
                # 제목 블록의 경로에는 "자기 자신"까지 포함한다.
                blocks.append(Block(BlockKind.HEADING, at(), item.text, heading_path=tuple(heading_stack)))
            # ── 목록 항목 ──
            elif isinstance(item, ListItem):
                blocks.append(Block(BlockKind.LIST_ITEM, at(), item.text, heading_path=path_now))
            # ── 일반 텍스트 ──
            elif item.label not in _SKIP_LABELS:
                blocks.append(Block(BlockKind.PARAGRAPH, at(), item.text, heading_path=path_now))

        for page, table in pending:
            emit_pdf_grid(table.grid, page, table.box, tuple(heading_stack))
        return blocks


# ───────────────────────── 직접 실행용 ─────────────────────────
# 터미널에서 파서를 간단히 시험해 볼 때 쓴다. (서비스 코드에서는 호출되지 않음)
#
# 실행 (backend 폴더에서):
#   python -m app.pipeline.parsing.docling.docling_parser
#
# 주의: "python docling_parser.py" 처럼 파일을 직접 실행하면
#       "from app.pipeline..." import가 실패한다. 반드시 -m 으로 실행할 것.
def _parent_cell_range(location: Location) -> str:
    start, end = location.parent_table_cell, location.parent_table_cell_end
    return f"{start}:{end}" if end and end != start else start or ""


def _numbered_reference_text(block: Block, table_numbers: dict) -> str | None:
    if block.table_reference_text is None:
        return None

    def renumber(match):
        child_key = (*block.location.table_key[:3], int(match[1]) - 1)
        number = table_numbers.get(child_key)
        return f"[중첩 표 {number} 참조]" if number is not None else match[0]

    return re.sub(r"\[중첩 표 (\d+) 참조\]", renumber, block.table_reference_text)


def _format_result(target: str, result: ParsedDocument) -> str:
    lines = [
        f"파일: {target}",
        f"형식={result.source_format}  블록={len(result.blocks)}개  경고={list(result.warnings)}",
        "-" * 70,
    ]
    depth: dict[tuple, int] = {}
    numbers = {
        block.location.table_key: block.table_number for block in result.blocks if block.kind.is_table
    }
    opened = set()
    for block in result.blocks:
        location = block.location
        level = 0
        key = location.table_key
        nested = location.parent_table_index is not None
        if nested:
            level = depth.get((*key[:3], location.parent_table_index), 0) + 1
        pad = " " * (level * 6)
        is_table = block.kind.is_table
        if is_table and key not in opened:
            opened.add(key)
            if location.index is not None:
                depth[key] = level
            label = block.table_number
            scope = ", ".join(
                f"{name}={value}" for name in ("page", "slide")
                if (value := getattr(location, name)) is not None
            )
            if nested and (cell_range := _parent_cell_range(location)):
                scope = ", ".join(filter(None, (scope, f"parent_table_cell={cell_range}")))
            heading = f"중첩 표 {label}" if nested else f"table {label}"
            lines.extend(("", f"{pad}[{heading}]" + (f" ({scope})" if scope else "")))
            if block.heading_path:
                path_text = " > ".join(" ".join(title.splitlines()) for title in block.heading_path)
                lines.append(f"{pad}    제목 경로: [{path_text}]")
        if is_table:
            pad += "    "
        else:
            lines.append("")
        shown = {
            field.name: repr(value) for field in fields(location)
            if (value := getattr(location, field.name)) is not None
        }
        for start, end in (("row", "end_row"), ("table_row", "table_end_row")):
            if start in shown and end in shown:
                shown[start] += f"~{shown.pop(end)}"
        where = ", ".join(f"{name}={value}" for name, value in shown.items())
        lines.append(f"{pad}[{block.kind.value} {block.kind_number}] Location({where})")
        if block.heading_path and not is_table and block.kind != BlockKind.HEADING:
            path_text = " > ".join(" ".join(title.splitlines()) for title in block.heading_path)
            lines.append(f"{pad}    제목 경로: [{path_text}]")
        display_text = _numbered_reference_text(block, numbers) or block.text
        lines.extend(f"{pad}    {line}" for line in display_text.splitlines())
        for cell in block.group_cells:
            if block.kind != BlockKind.TABLE_HEADER and cell.range not in display_text:
                source = next((value for value in block.table_cells if value.range == cell.range), None)
                if source and len(source.column_indexes) == 1 and source.row == source.end_row:
                    continue
                lines.append(f"{pad}    병합 셀 {cell.range}")
    return "\n".join(lines) + "\n"


def _write_parsed_result(target: str, result: ParsedDocument) -> Path:
    output_dir = Path(__file__).resolve().parent.parent / "parsing_test"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{Path(target).stem}.parsed.txt"
    output_path.write_text(_format_result(target, result), encoding="utf-8")
    return output_path


def main() -> None:
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = DoclingParser()
    print(f"파서: {parser.name} {parser.version}  (형식별 첫 실행에 모델을 불러옵니다)")
    while True:
        try:
            target = input("파싱할 파일 경로 (빈 입력으로 종료): ").strip().strip('"')
            if not target:
                break
            output_path = _write_parsed_result(target, parser.parse(target))
            print(f"저장 완료: {output_path.resolve()}")
        except (EOFError, KeyboardInterrupt):
            break
        except (ParseError, OSError) as exc:
            print(exc, file=sys.stderr)
