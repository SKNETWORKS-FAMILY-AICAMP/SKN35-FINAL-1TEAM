"""Docling 기반 문서 파서 (DocumentParser Port의 구현체).

역할
----
Docling이 만든 DoclingDocument(Docling 전용 자료구조)를
우리 파이프라인의 공통 결과 모델 ParsedDocument / Block 으로 "변환"한다.

    파일 ──Docling──▶ DoclingDocument ──이 파일──▶ ParsedDocument(Block, Block, ...)

Docling이 해 주는 일 : 레이아웃 분석, 읽기 순서 복원, 표 구조 인식, (스캔본) OCR
이 파일이 하는 일    : 항목 종류 분류, 제목 경로(heading_path) 계산,
                       표를 "열 이름: 값" 행 문장으로 풀기, 위치(Location) 매핑,
                       경고(warnings) 수집

base.py 규칙 (반드시 지킴)
-------------------------
- 읽을 수 없으면 ParseError. 읽었지만 일부가 이상하면 예외가 아니라 warnings.
- 텍스트와 표만 읽는다. 서식과 문서 안 이미지는 버린다.
- 정규화·마스킹·해시는 하지 않는다. 원문 그대로 돌려준다.
"""

from __future__ import annotations

import logging
from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path

from docling.datamodel.base_models import ConversionStatus
from docling.document_converter import DocumentConverter
from docling_core.types.doc import (
    DocItemLabel,
    ListItem,
    SectionHeaderItem,
    TableItem,
    TextItem,
    TitleItem,
)
from docling_core.types.doc.common.content_layer import ContentLayer

from app.pipeline.models import Block, BlockKind, Location, ParsedDocument
from app.pipeline.parsing.base import ParseError

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


def _to_location(item, fmt: str, order: int) -> Location:
    """Docling 항목의 위치를 우리 Location으로 바꾼다.

    형식별 규칙 (base.py 규칙 참고):
      - PDF  : 페이지 번호                      → Location(page=)
      - PPTX : 슬라이드 번호                    → Location(slide=)
      - 그 외(DOCX, XLSX): 문서 안 등장 순번    → Location(index=)

    order는 문서 안에서 블록이 나온 순번(0부터)이다.
    DOCX는 Docling이 페이지 번호를 주지 않는 경우가 많아 순번을 쓴다.
    """
    # prov = provenance(출처). 항목이 어느 페이지의 어디에 있었는지 담긴 목록.
    page = item.prov[0].page_no if getattr(item, "prov", None) else None

    if fmt == "pdf":
        # 페이지를 못 구했어도 순번이라도 남겨 출처 추적이 끊기지 않게 한다.
        return Location(page=page) if page is not None else Location(index=order)
    if fmt == "pptx":
        # PPTX는 page_no가 슬라이드 번호로 들어온다 (실제 파일로 확인 필요).
        return Location(slide=page) if page is not None else Location(index=order)
    # DOCX / XLSX
    # XLSX의 시트 이름·행 번호는 Docling 결과(prov)에서 얻을 수 없다.
    # 정확한 시트/행이 필요하면 openpyxl 기반 별도 파서를 두는 것을 권장한다.
    return Location(index=order)


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


def _column_names(df) -> list[str]:
    """DataFrame 열 이름을 문자열 리스트로 만든다.

    표에 헤더 행이 없으면 pandas가 0, 1, 2 같은 숫자를 열 이름으로 붙인다.
    숫자 열 이름은 의미가 없으므로 "열1", "열2" ... 로 바꾼다.
    """
    names: list[str] = []
    for i, col in enumerate(df.columns, start=1):
        label = str(col).strip()
        names.append(f"열{i}" if (not label or label.isdigit()) else label)
    return names


def _table_to_blocks(
    table: TableItem,
    doc,
    loc: Location,
    heading_path: tuple[str, ...],
    warnings: list[str],
) -> list[Block]:
    """표 하나를 행 단위 Block(TABLE_ROW) 여러 개로 푼다.

    각 행은 "열 이름: 값, 열 이름: 값" 형태의 한 문장이 된다.
        | 항목 | 내용 |          →   "항목: 로그인, 내용: 아이디로 인증"
        | 로그인 | 아이디로 인증 |
    이렇게 하면 행 하나만 따로 검색·청킹돼도 의미가 유지된다.

    - 병합 셀은 Docling이 격자(grid)로 펼쳐 주므로 같은 값이 채워진다.
    - context에는 헤더(열 이름들)를 넣어 검색용 접두 정보로 쓴다.
    - 값이 빈 칸은 문장에서 뺀다. 행 전체가 비면 그 행은 건너뛴다.
    """
    try:
        df = table.export_to_dataframe(doc)
    except Exception as exc:  # 표 구조가 깨진 경우 — 문서 전체를 실패시키지 않는다
        warnings.append(f"표 변환 실패(page={loc.page}, index={loc.index}): {exc}")
        return []

    if df.empty and len(df.columns) == 0:
        return []

    columns = _column_names(df)
    context = ", ".join(columns)
    blocks: list[Block] = []

    for row in df.itertuples(index=False, name=None):
        # zip으로 (열 이름, 값) 짝을 만든다. 열 이름이 중복돼도 안전하다.
        pairs = [
            f"{col}: {str(val).strip()}"
            for col, val in zip(columns, row)
            if str(val).strip() and str(val).strip().lower() != "nan"
        ]
        if not pairs:
            continue    # 완전히 빈 행
        blocks.append(
            Block(
                kind=BlockKind.TABLE_ROW,
                location=loc,
                text=", ".join(pairs),
                heading_path=heading_path,
                context=context,
            )
        )
    return blocks


# ───────────────────────── 파서 본체 ─────────────────────────

class DoclingParser:
    """Docling으로 PDF / DOCX / PPTX / XLSX 를 ParsedDocument로 변환하는 파서.

    DocumentParser Protocol(base.py)의 규격을 따른다.
    """

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
            self._converter = DocumentConverter()
        return self._converter

    def parse(self, path: str) -> ParsedDocument:
        """파일 하나를 ParsedDocument로 바꾼다.

        Raises:
            ParseError: 파일이 없거나, 지원하지 않는 형식이거나, 변환에 실패한 경우.
        """
        # 1) 사전 검사 — 파일 존재 여부와 형식
        if not Path(path).is_file():
            raise ParseError(f"파일을 찾을 수 없음: {path}")
        fmt = _source_format(path)

        # 2) Docling 변환 — 파일 손상 등으로 실패하면 ParseError로 통일해서 던진다.
        try:
            result = self._get_converter().convert(path, raises_on_error=True)
        except Exception as exc:
            raise ParseError(f"Docling 변환 실패: {path} ({exc})") from exc

        warnings: list[str] = []

        # 일부 페이지만 성공한 경우: 예외는 아니지만 결과가 불완전하므로 알린다.
        if result.status == ConversionStatus.PARTIAL_SUCCESS:
            warnings.append("일부 페이지/요소 변환 실패 (partial_success)")
        elif result.status != ConversionStatus.SUCCESS:
            raise ParseError(f"Docling 변환 상태 이상: {result.status}")

        doc = result.document

        # 3) DoclingDocument를 읽기 순서대로 돌며 Block으로 변환
        blocks: list[Block] = []
        heading_stack: list[str] = []    # 현재 위치의 제목 경로
        title_depth = 0                  # 문서 제목(Title)이 스택에서 차지하는 칸 수

        # iterate_items: (항목, 깊이)를 문서 읽기 순서대로 돌려준다.
        # included_content_layers로 본문(BODY)만 받는다.
        for item, _depth in doc.iterate_items(included_content_layers=_BODY_ONLY):
            order = len(blocks)                       # 지금까지 만든 블록 수 = 이 블록의 순번
            loc = _to_location(item, fmt, order)
            path_now = tuple(heading_stack)           # 이 블록이 속한 제목 경로 (불변 tuple)

            # ── 문서 제목 ──
            # TitleItem은 TextItem의 하위 클래스이므로 반드시 TextItem보다 먼저 검사한다.
            if isinstance(item, TitleItem):
                if not item.text.strip():
                    continue
                heading_stack = [item.text]
                title_depth = 1
                blocks.append(
                    Block(BlockKind.HEADING, loc, item.text, heading_path=tuple(heading_stack))
                )

            # ── 섹션 제목 ──
            elif isinstance(item, SectionHeaderItem):
                if not item.text.strip():
                    continue
                heading_stack = _update_heading_stack(
                    heading_stack, title_depth, item.level, item.text
                )
                # 제목 블록의 경로에는 "자기 자신"까지 포함한다.
                blocks.append(
                    Block(BlockKind.HEADING, loc, item.text, heading_path=tuple(heading_stack))
                )

            # ── 목록 항목 ──
            elif isinstance(item, ListItem):
                if item.text.strip():
                    blocks.append(
                        Block(BlockKind.LIST_ITEM, loc, item.text, heading_path=path_now)
                    )

            # ── 표 ──
            elif isinstance(item, TableItem):
                # 한 표가 여러 행 Block이 된다. 모든 행이 같은 Location을 갖는다.
                blocks.extend(_table_to_blocks(item, doc, loc, path_now, warnings))

            # ── 일반 텍스트 (본문 문단) ──
            # ListItem, SectionHeaderItem, TitleItem은 위에서 이미 처리했다.
            elif isinstance(item, TextItem):
                if item.label in _SKIP_LABELS:
                    continue
                if item.text.strip():
                    blocks.append(
                        Block(BlockKind.PARAGRAPH, loc, item.text, heading_path=path_now)
                    )

            # 그림(PictureItem) 등 나머지는 의도적으로 무시한다. (규칙: 이미지는 읽지 않음)

        # 4) 결과 점검 — 블록이 하나도 없으면 스캔본/빈 문서일 가능성이 크다.
        if not blocks:
            warnings.append("추출된 텍스트가 없음 (스캔본 또는 빈 문서 의심)")

        return ParsedDocument(
            blocks=tuple(blocks),            # list 대신 tuple (frozen dataclass)
            source_format=fmt,
            warnings=tuple(warnings),
        )


# ───────────────────────── 직접 실행용 ─────────────────────────
# 터미널에서 파서를 간단히 시험해 볼 때 쓴다. (서비스 코드에서는 호출되지 않음)
#
# 실행 (backend 폴더에서):
#   python -m app.pipeline.parsing.docling_parser                 # 기본 샘플 파싱
#   python -m app.pipeline.parsing.docling_parser "다른파일.pdf"   # 파일 지정
#
# 주의: "python docling_parser.py" 처럼 파일을 직접 실행하면
#       "from app.pipeline..." import가 실패한다. 반드시 -m 으로 실행할 것.
if __name__ == "__main__":
    import sys

    # 기본 샘플: <프로젝트>/data/docset/1팀_파트별_일정표_261117.pdf
    # 이 파일 위치: backend/app/pipeline/parsing/ → parents[4] = 프로젝트 루트
    _default = Path(__file__).resolve().parents[4] / "data" / "docset" / "1팀_파트별_일정표_261117.pdf"
    _target = sys.argv[1] if len(sys.argv) > 1 else str(_default)

    # Windows 콘솔(cp949)에서 한글/특수문자 출력이 깨지거나 에러 나는 것을 방지
    sys.stdout.reconfigure(encoding="utf-8")

    print(f"파일: {_target}")
    _parser = DoclingParser()
    print(f"파서: {_parser.name} {_parser.version}  (첫 실행은 모델 로딩 때문에 오래 걸릴 수 있음)")

    _result = _parser.parse(_target)
    print(f"형식={_result.source_format}  블록={len(_result.blocks)}개  경고={list(_result.warnings)}")
    print("-" * 70)

    for _b in _result.blocks:
        print(f"[{_b.kind.value}] {_b.location}")
        if _b.heading_path:
            print(f"    제목경로: {' > '.join(_b.heading_path)}")
        if _b.context:
            print(f"    context : {_b.context}")
        print(f"    {_b.text}")
