"""
* HWP·HWPX 파서: kordoc 어댑터
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any

from lxml import etree

from backend.app.pipeline.parsing.hwp.hwp_headings import apply_headings

Block = dict[str, Any]

PARSER_NAME = "kordoc"

_SAFE_PARSER = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=False)
_SECTION_RE = re.compile(r"Contents/section(\d+)\.xml$")

_IMAGE_PARA_RE = re.compile(r"^\s*(\[이미지:[^\]]*\]\s*)+$")   # 이미지 자리만 있는 문단
_INLINE_TAG_RE = re.compile(r"</?(sup|sub|u|b|i|s|br)\s*/?>")  # kordoc이 글 안에 넣는 HTML 태그
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")       # kordoc이 글 안에 넣는 마크다운 그림 ![image](id)


def clean_text(text: str) -> str:
    """kordoc이 글에 붙인 표지를 원문 글자로 되돌린다 (정규화는 하지 않음)."""
    text = _MD_IMAGE_RE.sub("", text)
    text = _INLINE_TAG_RE.sub("", text)
    return text.replace("\\$", "$")  # kordoc은 원문 '$'를 '\$'로 담는다


def _ws(s: str) -> str:
    """비교 키: 공백과 칸 구분자(/ |)를 뺀 글자.
    kordoc은 한 줄짜리 표(꼬리말 등)를 "법제처 / - / 국가법령정보센터"처럼 / 로 이어 문단으로 내기 때문."""
    return re.sub(r"[\s/|]+", "", s)


def hwpx_header_footer_texts(path: str | Path) -> set[str]:
    """HWPX 머리말·꼬리말 문단 글자 (공백 제거). HWP·읽기 실패면 빈 집합."""
    path = Path(path)
    if path.suffix.lower() != ".hwpx":
        return set()
    out: set[str] = set()
    try:
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if not _SECTION_RE.match(n):
                    continue
                root = etree.fromstring(z.read(n), parser=_SAFE_PARSER)
                for hf in root.iter("{*}header", "{*}footer"):
                    for p in hf.iter("{*}p"):
                        t = _ws("".join(t.text or "" for t in p.iter("{*}t")))
                        if t:
                            out.add(t)
    except (zipfile.BadZipFile, etree.XMLSyntaxError, KeyError):
        return set()
    return out


def _cells(table: dict[str, Any]) -> list[dict[str, Any]]:
    """kordoc 표(cells[행][열]) → 칸 목록 (hwpx_parser.parse_table과 같은 형식)"""
    out = []
    for r, row in enumerate(table.get("cells", [])):
        for c, cell in enumerate(row):
            item: dict[str, Any] = {
                "row": r,
                "col": c,
                "row_span": cell.get("rowSpan", 1),
                "col_span": cell.get("colSpan", 1),
                "text": clean_text(cell.get("text", "")),
            }
            inner = [b["table"] for b in cell.get("blocks") or [] if b.get("type") == "table"]
            if inner:
                # 칸 text는 kordoc이 안쪽 표 글자까지 평탄화한 것 → 칸 자기 문단만 남긴다
                item["text"] = clean_text("\n".join(
                    b.get("text", "") for b in cell["blocks"] if b.get("type") != "table"
                )).strip()
                item["tables"] = [_cells(t) for t in inner]
            out.append(item)
    return out


def kordoc_to_blocks(raw_blocks: list[dict[str, Any]], drop_texts: set[str] = frozenset()) -> list[Block]:
    """kordoc 블록 → 우리 블록. drop_texts(공백 뺀 글자)와 같은 문단은 뺀다(머리말·꼬리말)."""
    blocks: list[Block] = []

    def add(block: Block) -> None:
        block["order"] = len(blocks) + 1
        blocks.append(block)

    def walk(items: list[dict[str, Any]], para_no: int | None = None) -> None:
        for i, b in enumerate(items, start=1):
            no = para_no if para_no is not None else i
            locator = {"kind": "paragraph", "para_no": no}
            if b.get("pageNumber"):
                locator["page"] = b["pageNumber"]
            t = b.get("type")
            if t in ("paragraph", "heading"):
                # kordoc 제목도 일단 문단으로 → apply_headings가 다시 판단
                text = clean_text(b.get("text") or "").strip()
                if text and not _IMAGE_PARA_RE.match(text) and _ws(text) not in drop_texts:
                    add({"type": "paragraph", "text": text, "locator": locator})
            elif t == "table" and b.get("table"):
                cells = _cells(b["table"])
                filled = [_ws(c["text"]) for c in cells if _ws(c["text"])]
                if filled and drop_texts and all(x in drop_texts for x in filled):
                    continue  # 머리말·꼬리말 안의 표 (예: "법제처 | 국가법령정보센터")
                add({"type": "table", "cells": cells, "locator": locator})
            elif t == "list":
                text = clean_text(b.get("text") or "").strip()
                if text:
                    add({"type": "paragraph", "text": text, "locator": locator})
                walk(b.get("children") or [], para_no=no)
            # image·separator: 글자가 없어 버림
            if b.get("footnoteText"):
                add({"type": "paragraph", "text": clean_text(b["footnoteText"]).strip(),
                     "locator": {**locator, "kind": "footnote"}})

    walk(raw_blocks)
    return apply_headings(blocks)


def parse_hwp(path: str | Path, client: Any) -> list[Block]:
    """HWP·HWPX 파일을 kordoc으로 읽어 블록 목록으로. client: kordoc.KordocClient (호출하는 쪽이 관리)."""
    path = Path(path).resolve()  # kordoc 워커는 작업 폴더가 달라서 절대 경로로 보낸다
    result = client.parse(str(path))
    if not result.success:
        raise ValueError(f"kordoc 파싱 실패 ({result.code}): {result.error}")
    return kordoc_to_blocks(result.blocks, drop_texts=hwpx_header_footer_texts(path))
