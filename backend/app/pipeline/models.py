"""파이프라인 단계들이 주고받는 데이터 상자 (순수 Python)"""

# 파이프라인 단계들이 서로 주고받는 데이터의 모양(데이터 클래스)을 정의합니다. 
# 추출·비교·판정 사이에서 오가는 값 객체입니다.


from collections import Counter
from dataclasses import dataclass, replace
from enum import Enum


class BlockKind(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    TABLE_TITLE = "table_title"
    TABLE_HEADER = "table_header"
    TABLE_ROW = "table_row"
    TABLE_ROW_GROUP = "table_row_group"     # 병합 셀 그룹

    @property
    def is_table(self) -> bool:
        return self.value.startswith("table_")


@dataclass(frozen=True)
class Location:
    """원본 위치. 형식에 해당하는 항목만 채운다. 출처 표시용이며 비교 키가 아니다."""
    page: int | None = None     #pdf
    slide: int |  None = None   #pptx
    sheet: str | None = None    #xlsx 시트명
    row: int | None = None      #xlsx 행 번호
    index: int | None = None    #Docx, md, txt, hwpx 문단 번호
    end_row:int | None = None   #Xlsx 그룹의 마지막 원본 행, 포함
    parent_table_index: int | None = None  # DOCX 중첩 표를 담는 바깥 표
    parent_table_cell: str | None = None  # DOCX 바깥 표의 셀 주소 (예: A2)
    parent_table_cell_end: str | None = None
    table_row: int | None = None  # DOCX 표의 원본 행 번호
    table_end_row: int | None = None

    @property
    def table_key(self) -> tuple[int | None, int | None, str | None, int | None]:
        return self.page, self.slide, self.sheet, self.index


# 병합 셀 그룹 정보
@dataclass(frozen=True)
class GroupCell:
    range: str                      # 병합 범위 (ex:"A4:B6")
    headers: tuple[str, ...]        # ex: ("구분", "용어/역할"),
    value: str                      # 내용 (ex: "역할" )


@dataclass(frozen=True)
class TableCell:
    row: int
    end_row: int
    range: str
    column_indexes: tuple[int, ...]  # table_columns의 0-based 인덱스
    value: str


@dataclass(frozen=True)
class Block:
    """파서가 뽑은 항목. 원문 그대로이며 해시는 아직 없다."""
    kind: BlockKind
    location: Location      #위치
    text: str               # 원문 
    heading_path: tuple[str, ...] = ()      #제목 경로
    group_cell: GroupCell | None = None         #표의 병합 범위·헤더·값
    context: str = ""        #표 헤더, 시트명 등 검색용 접두 정보
    table_columns: tuple[str, ...] = ()
    table_header_rows: int = 0
    table_rows: tuple[tuple[str | None, ...], ...] = ()  # table_columns 순서, 빈 셀은 None
    group_cells: tuple[GroupCell, ...] = ()
    table_reference_text: str | None = None
    kind_number: int | None = None
    table_number: int | None = None
    table_cells: tuple[TableCell, ...] = ()
    table_column_spans: tuple[tuple[int, int], ...] = ()  # 원본 격자의 [시작, 끝) 열


@dataclass(frozen=True)
class ParsedDocument:
    """파일 하나를 파싱한 결과 전체"""
    blocks: tuple[Block, ...]       #list 대신 tuple
    source_format: str      #pdf | docx | pptx | xlsx
    warnings: tuple[str, ...] = ()      #파싱 중 경고(스캔본 의심, 병합셀 등)

    def __post_init__(self) -> None:
        counts = Counter()
        tables = {}
        numbered = []
        for block in self.blocks:
            counts[block.kind] += 1
            table_number = None
            if block.kind.is_table:
                table_number = tables.setdefault(block.location.table_key, len(tables) + 1)
            numbered.append(replace(block, kind_number=counts[block.kind], table_number=table_number))
        object.__setattr__(self, "blocks", tuple(numbered))





# ───────────── 청킹 이후 결과 (10단계~) ─────────────

@dataclass(frozen=True)
class Paragraph:
    """정규화·마스킹을 마친 문단. 변경 분석(diff)의 비교 단위."""
    order: int                       # 문서 안 순번
    text: str                        # 정규화·마스킹된 텍스트
    hash: str                        # 문단 해시 (text 기준)
    occurrence: int                  # 같은 해시의 등장 순번 → (hash, occurrence)로 구분
    location: Location               # 출처 구간
    is_noise: bool = False           # 노이즈 필터 결과 (11단계)
    injection_flag: bool = False     # 프롬프트 인젝션 의심 표시 (9단계)


@dataclass(frozen=True)
class Entity:
    """문단에서 찾은 요구사항 번호·화면 번호·API명 (12단계)."""
    paragraph_order: int             # 속한 문단의 order
    kind: str                        # "REQ" | "SCR" | "API"
    value: str                       # 정규화된 값 (예: "REQ-023")
