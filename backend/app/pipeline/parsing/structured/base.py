"""문서 파서 Port. 구현체(docling, hwpx, text …)는 이 규격만 맞추면 된다.


- 모든 파서는 이 규격 뒤에 두고, 공통 결과 모델(ParsedDocument)로 변환한다.
  이후 단계는 파일 형식을 알지 못한다.
- 파서 이름과 버전은 문서 버전 기록에 남긴다 (버전이 바뀌면 문단 분할이 달라질 수 있음).
"""

from importlib.metadata import version
from pathlib import Path
from typing import Protocol

from app.pipeline.models import Block, ParsedDocument


class ParseError(Exception):
    """파일을 읽을 수 없어 파싱이 불가능한 경우 (파일 손상, 지원하지 않는 형식 등).

    읽었지만 일부가 이상한 경우(병합 셀, 빈 페이지 등)는 예외가 아니라
    ParsedDocument.warnings에 담는다.
    """


class DocumentParser(Protocol):
    """파일 하나를 ParsedDocument로 바꾸는 파서의 규격서."""

    name: str                       # 예: "docling"  → 문서 버전 기록에 저장
    version: str                    # 예: "2.150.1"  → 문서 버전 기록에 저장
    extensions: tuple[str, ...]     # 예: ("pdf", "docx")  → registry가 매핑에 사용 (점·대문자 없이)

    def parse(self, path: str) -> ParsedDocument:
        """파일 경로를 받아 ParsedDocument를 돌려준다.

        규칙:
        - 읽을 수 없으면 ParseError를 던진다.
        - 텍스트와 표만 읽는다. 서식과 문서 안 이미지는 읽지 않는다.
        - 표는 행 단위로 "열 이름: 값" 문장으로 풀고, 병합 셀은 풀어서 채운다.
        - 위치(Location)는 형식에 맞게 채운다: PDF 페이지, PPTX 슬라이드,
          XLSX 시트 이름·행 번호, 그 외 문단 순번.
        - 정규화·마스킹·해시는 하지 않는다. 원문을 그대로 돌려주고,
          이후 단계(정규화 → 마스킹 → 청킹)가 처리한다.
        """
        ...


class FormatParser:
    """하위 클래스는 name, extensions, _package와 _read()만 정한다."""

    name: str
    extensions: tuple[str, ...]
    _package: str

    @property
    def version(self) -> str:
        return version(self._package)

    def parse(self, path: str) -> ParsedDocument:
        suffix = Path(path).suffix.lower().lstrip(".")
        if suffix not in self.extensions:
            raise ParseError(f"지원하지 않는 형식: {suffix!r}")
        if not Path(path).is_file():
            raise ParseError(f"파일을 찾을 수 없음: {path}")
        warnings: list[str] = []
        try:
            blocks = self._read(path, warnings)
        except ParseError:
            raise
        except Exception as exc:
            raise ParseError(f"문서 변환 실패: {path} ({exc})") from exc
        if not blocks:
            warnings.append("추출된 텍스트가 없음 (스캔본 또는 빈 문서 의심)")
        return ParsedDocument(blocks=tuple(blocks), source_format=suffix, warnings=tuple(warnings))

    def _read(self, path: str, warnings: list[str]) -> list[Block]:
        raise NotImplementedError
