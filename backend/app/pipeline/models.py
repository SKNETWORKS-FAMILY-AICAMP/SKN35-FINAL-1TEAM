"""파이프라인 단계들이 주고받는 데이터 상자 (순수 Python)"""

# 파이프라인 단계들이 서로 주고받는 데이터의 모양(데이터 클래스)을 정의합니다. 
# 추출·비교·판정 사이에서 오가는 값 객체입니다.


from dataclasses import dataclass
from enum import Enum


class BlockKind(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    TABLE_ROW = "table_row"


@dataclass(frozen=True)
class Location:
    """원본 위치. 형식에 해당하는 항목만 채운다. 출처 표시용이며 비교 키가 아니다."""
    page: int | None = None     #pdf
    slide: int |  None = None   #pptx
    sheet: str | None = None    #xlsx 시트명
    row: int | None = None      #xlsx 행 번호
    index: int | None = None    #Docx, md, txt, hwpx 문단 번호


@dataclass(frozen=True)
class Block:
    """파서가 뽑은 항목. 원문 그대로이며 해시는 아직 없다."""
    kind: BlockKind
    location: Location      #위치
    text: str               # 원문 
    heading_path: tuple[str, ...] = ()      #제목 경로
    context: str = ""        #표 헤더, 시트명 등 검색용 접두 정보


@dataclass(frozen=True)
class ParsedDocument:
    """파일 하나를 파싱한 결과 전체"""
    blocks: tuple[Block, ...]       #list 대신 tuple
    source_format: str      #pdf | docx | pptx | xlsx
    warnings: tuple[str, ...] = ()      #파싱 중 경고(스캔본 의심, 병합셀 등)





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