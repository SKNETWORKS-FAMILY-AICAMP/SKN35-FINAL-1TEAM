"""
* HWPX 파서 뼈대
* HWPX: parse_hwpx (구역·문단 순회, 블록 조립)
"""


from __future__ import annotations  # 최신 타입 표기를 옛 파이썬 버전에서도 쓸 수 있게 해줌

import logging                      # 경고 남기기 (파일 하나 때문에 전체가 멈추지 않게)
import re                           # 정규식
import zipfile                      # HWPX(zip) 열기
from pathlib import Path            # 파일 경로를 운영체제와 상관없이 다루기 (Mac·Windows 공통)
from typing import Any, Callable    # 타입 힌트 (아무값, 함수)

from lxml import etree              # XML 읽기

from backend.app.pipeline.parsing.hwp.hwp_headings import apply_headings

logger = logging.getLogger(__name__)

# 사용자가 올린 파일 안전 검사
# resolve_entities=False: XML 안의 "외부 파일 읽어 와" 같은 명령(XXE 공격) 무시
# no_network=True: XML이 인터넷 접속 막음
# huge_tree=False: 비정상적으로 깊거나 큰 XML 거부
_SAFE_PARSER = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)

_SECTION_RE = re.compile(r"Contents/section(\d+)\.xml$")
_HEADING_STYLE_RE = re.compile(r"^개요\s*(\d+)$")
_OUTLINE_ENG_RE = re.compile(r"^Outline\s*(\d+)$")

# 글자 대신 빈 태그로 저장되는 특수 문자 → 실제 글자로 바꿈
# itertext()는 빈 태그를 무시해서 "알림은<tab/>2일"이 "알림은2일"로 붙어 버림
_INLINE_CHARS = {
    "tab": "\t",
    "lineBreak": "\n",
    "nbSpace": " ",   # 줄바꿈 안 되는 공백
    "fwSpace": "　",   # 전각 공백
    "hyphen": "-",
}

# subList: 글상자·각주·미주·머리말·꼬리말·메모·표 칸이 모두 자기 문단을 이 안에 둠
_EMBEDDED_KINDS = {
    "drawText": "textbox",   # 글상자 (rect·ellipse 등 도형 안의 글)
    "footNote": "footnote",  # 각주
    "endNote": "endnote",    # 미주
}
# 머리말·꼬리말·숨은 설명·메모: 쪽마다 반복되거나 본문이 아님 → 버린다
_DROPPED_PARENTS = {"header", "footer", "hiddenComment", "memo"}

Block = dict[str, Any]


# zip에서 읽은 바이트를 XML 트리로 변환
def _parse_xml(data: bytes) -> etree._Element:
    return etree.fromstring(data, parser=_SAFE_PARSER)

# 태그 이름에서 네임스페이스 주소 떼고 끝 이름만 돌려줌
def ln(el: etree._Element) -> str:
    """태그의 끝 이름(localname). 네임스페이스 주소는 버전마다 다를 수 있어 무시한다."""
    return etree.QName(el).localname


# header.xml에서 "이 스타일·문단 모양이면 몇 단계 제목"을 읽음
def load_heading_levels(z: zipfile.ZipFile) -> tuple[dict[str, int], dict[str, int]]:
    """(스타일 id -> 제목 레벨, 문단 모양 id -> 제목 레벨). 레벨은 1부터.

    - 스타일: 이름이 '개요 N' (영문 한글은 engName 'Outline N')
    - 문단 모양(paraPr): <hh:heading type="OUTLINE" level="0"/> (level은 0부터라 +1)
      스타일 없이 [서식 > 문단 모양]에서 개요를 고른 문단을 잡는다.
    header.xml이 없으면 둘 다 빈 사전 (제목은 apply_headings의 글자 모양 규칙으로만 찾음).
    """
    try:
        data = z.read("Contents/header.xml")
    except KeyError:
        logger.warning("HWPX에 Contents/header.xml이 없어 스타일(제목 단계) 없이 읽음")
        return {}, {}
    head = _parse_xml(data)
    style_levels: dict[str, int] = {}
    parapr_levels: dict[str, int] = {}
    for el in head.iter():
        if not isinstance(el.tag, str):  # 주석 등
            continue
        name = ln(el)
        if name == "style":
            m = _HEADING_STYLE_RE.search(el.get("name", "")) or _OUTLINE_ENG_RE.search(el.get("engName", ""))
            if m:
                style_levels[el.get("id")] = int(m.group(1))
        elif name == "heading" and el.get("type") == "OUTLINE":
            pp = el.getparent()
            level = _int_attr(el, "level")
            if pp is not None and ln(pp) == "paraPr" and level is not None:
                parapr_levels[pp.get("id")] = level + 1
    return style_levels, parapr_levels


# hp:t 하나의 글자 (탭·줄바꿈 등 빈 태그도 글자로 바꿈)
def t_text(t: etree._Element) -> str:
    """<hp:t>알림은<hp:tab/>2일</hp:t> → '알림은\\t2일'"""
    parts = [t.text or ""]
    for ch in t:
        parts.append(_INLINE_CHARS.get(ln(ch), ""))
        parts.append(ch.tail or "")
    return "".join(parts)


# 글자만 추출
def _ignore(*_args: Any) -> None:
    return None


def walk_own(
    el: etree._Element,
    on_text: Callable[[str], None],
    on_table: Callable[[etree._Element], None],
    on_embedded: Callable[[str, etree._Element], None] = _ignore,
) -> None:
    """이 문단의 글자만 모으고, 표·글상자·각주는 따로 넘김 (그 안으로 내려가지 않음)

    on_embedded(kind, subList): 글상자·각주·미주의 subList. 머리말·꼬리말은 버린다.
    """
    for ch in el:
        name = ln(ch)
        if name == "tbl":  # 표
            on_table(ch)
        elif name == "subList":  # 글상자·각주·머리말 등의 문단
            parent = ln(el)
            if parent in _EMBEDDED_KINDS:
                on_embedded(_EMBEDDED_KINDS[parent], ch)
            elif parent not in _DROPPED_PARENTS:
                logger.warning("HWPX에서 처리하지 않는 subList(부모 %s)를 건너뜀", parent)
        elif name == "t":  # 글자
            on_text(t_text(ch))
        elif name in _INLINE_CHARS:  # hp:t 밖에 놓인 탭·줄바꿈
            on_text(_INLINE_CHARS[name])
        else:
            walk_own(ch, on_text, on_table, on_embedded)  # 그 밖(run, ctrl, rect 등)


def _children(el: etree._Element, name: str) -> list[etree._Element]:
    """바로 아래 자식 중 이름이 name인 것 (손자 이하는 보지 않음)"""
    return [e for e in el if ln(e) == name]


def _int_attr(el: etree._Element | None, attr: str, default: int | None = None) -> int | None:
    """속성을 정수로 읽는다. 없거나 숫자가 아니면 default."""
    if el is None:
        return default
    try:
        return int(el.get(attr))
    except (TypeError, ValueError):
        return default


def _sublist_text(sub: etree._Element) -> str:
    """글상자·각주 subList의 글자 (안의 표·글상자는 글자만 줄바꿈으로 이어 붙임)"""
    paras: list[str] = []
    for p in _children(sub, "p"):
        texts: list[str] = []
        walk_own(
            p, texts.append,
            lambda t: texts.append("\n" + _table_text(parse_table(t))),
            lambda _k, s: texts.append("\n" + _sublist_text(s)),
        )
        paras.append("".join(texts))
    return "\n".join(paras).strip()


def _table_text(cells: list[dict[str, Any]]) -> str:
    """칸 목록의 글자를 줄바꿈으로 이은 것 (안쪽 표·글상자 포함)"""
    out: list[str] = []
    for c in cells:
        out.append(c["text"])
        out.extend(_table_text(t) for t in c.get("tables", []))
        out.extend(e["text"] for e in c.get("embedded", []))
    return "\n".join(x for x in out if x)


def parse_table(tbl: etree._Element) -> list[dict[str, Any]]:
    """표 하나를 칸 목록으로 바꾼다. 칸마다 위치(row, col), 병합 크기, 글자.

    구조: tbl > tr > tc > subList > p
    - text: 칸의 자기 문단 글자만 (안쪽 표 글자는 섞지 않음)
    - tables: 칸 안의 표 → 같은 형식의 칸 목록 (있을 때만)
    - embedded: 칸 안의 글상자·각주 → [{"kind", "text"}] (있을 때만)
    """
    cells = []
    for tr in _children(tbl, "tr"):
        for tc in _children(tr, "tc"):
            addr = next(iter(_children(tc, "cellAddr")), None)
            row = _int_attr(addr, "rowAddr")
            col = _int_attr(addr, "colAddr")
            if row is None or col is None:
                logger.warning("HWPX 표 칸에 cellAddr(rowAddr·colAddr)가 없어 건너뜀")
                continue
            span = next(iter(_children(tc, "cellSpan")), None)

            paras: list[str] = []
            inner_tables: list[list[dict[str, Any]]] = []
            embedded: list[dict[str, str]] = []
            for sub in _children(tc, "subList"):
                for p in _children(sub, "p"):
                    texts: list[str] = []
                    walk_own(
                        p, texts.append,
                        lambda t: inner_tables.append(parse_table(t)),
                        lambda k, s: embedded.append({"kind": k, "text": _sublist_text(s)}),
                    )
                    paras.append("".join(texts))

            cell: dict[str, Any] = {
                "row": row,
                "col": col,
                "row_span": _int_attr(span, "rowSpan", 1),
                "col_span": _int_attr(span, "colSpan", 1),
                "text": "\n".join(paras).strip(),
            }
            if inner_tables:
                cell["tables"] = inner_tables
            kept = [e for e in embedded if e["text"]]
            if kept:
                cell["embedded"] = kept
            cells.append(cell)
    return cells


# 전체 조립
def parse_hwpx(path: str | Path) -> list[Block]:
    """HWPX 파일을 블록 목록으로 바꾼다.

    블록 1개 = 문단 1개 또는 표 1개.
    locator의 para_no는 모든 구역을 통틀어 1부터 세는 최상위 문단 번호이고,
    표·글상자·각주는 자기를 담은 최상위 문단의 번호를 쓴다.
    locator.kind: paragraph(본문) / textbox(글상자) / footnote(각주) / endnote(미주).
    글상자·각주 블록은 자기를 담은 문단 바로 뒤에 온다.

    제목: 개요 스타일·개요 문단 모양이면 여기서 정하고(heading_source="style"),
    없으면 apply_headings()가 글자 모양(제N장, 1., 가. …)으로 찾는다. heading_path도 거기서 채운다.
    """
    blocks: list[Block] = [] # 결과 목록
    para_no = 0 # 최상위 문단 번호 (출처 표시용)

    def add(block: Block) -> None:
        block["order"] = len(blocks) + 1
        blocks.append(block)

    def add_embedded(kind: str, sub: etree._Element, base: dict[str, Any]) -> None:
        """글상자·각주 안의 문단·표를 별도 블록으로 (안에 또 글상자가 있으면 이어서)"""
        locator = {**base, "kind": kind}
        for p in _children(sub, "p"):
            texts: list[str] = []
            tables: list[etree._Element] = []
            subs: list[tuple[str, etree._Element]] = []
            walk_own(p, texts.append, tables.append, lambda k, s: subs.append((k, s)))
            text = "".join(texts).strip()
            if text:
                add({"type": "paragraph", "text": text, "locator": dict(locator)})
            for tbl in tables:
                add({"type": "table", "cells": parse_table(tbl), "locator": dict(locator)})
            for k, s in subs:
                add_embedded(k, s, base)

    # with 사용하면 작업 끝나면 zip 파일 자동으로 닫힘 (에러나도)
    with zipfile.ZipFile(Path(path)) as z:
        style_levels, parapr_levels = load_heading_levels(z)
        sections = sorted(
            (n for n in z.namelist() if _SECTION_RE.match(n)),
            key=lambda n: int(_SECTION_RE.match(n).group(1)),
        )
        for sec in sections:
            sec_no = int(_SECTION_RE.match(sec).group(1))
            root = _parse_xml(z.read(sec))
            for p in (e for e in root if ln(e) == "p"):  # 최상위 문단만
                para_no += 1
                locator = {"kind": "paragraph", "section": sec_no, "para_no": para_no}

                texts: list[str] = []
                tables: list[etree._Element] = []
                subs: list[tuple[str, etree._Element]] = []
                walk_own(p, texts.append, tables.append, lambda k, s: subs.append((k, s)))
                text = "".join(texts).strip()
                level = style_levels.get(p.get("styleIDRef")) or parapr_levels.get(p.get("paraPrIDRef"))

                if text and level:  # 개요 스타일·문단 모양으로 정한 제목
                    add({"type": "heading", "level": level, "text": text,
                         "heading_source": "style", "locator": dict(locator)})
                elif text:
                    add({"type": "paragraph", "text": text, "locator": dict(locator)})
                for tbl in tables:
                    add({"type": "table", "cells": parse_table(tbl), "locator": dict(locator)})
                for kind, sub in subs:
                    add_embedded(kind, sub, locator)
    return apply_headings(blocks)
