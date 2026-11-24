"""
* 제목 감지 (HWP·HWPX 공통)
"""

from __future__ import annotations

import re
from typing import Any

Block = dict[str, Any]

# (이름, 정규식) — 위에 있을수록 상위 제목
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("편", re.compile(r"^제\s*\d+\s*편(\s|$)")),
    ("장", re.compile(r"^제\s*\d+\s*장(\s|$)")),
    ("절", re.compile(r"^제\s*\d+\s*절(\s|$)")),
    ("관", re.compile(r"^제\s*\d+\s*관(\s|$)")),
    ("로마숫자", re.compile(r"^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+\s*[.\s]")),
    ("숫자", re.compile(r"^\d{1,2}\.\s")),           # 1. (1.5 같은 소수는 뒤에 공백이 없어 제외)
    ("숫자.숫자", re.compile(r"^\d{1,2}\.\d{1,2}\.?\s")),  # 1.1 / 1.1.
    ("숫자)", re.compile(r"^\d{1,2}\)\s")),
    ("한글", re.compile(r"^[가나다라마바사아자차카타파하]\.\s")),
    ("한글)", re.compile(r"^[가나다라마바사아자차카타파하]\)\s")),
    ("(숫자)", re.compile(r"^\(\d{1,2}\)\s")),
    ("(한글)", re.compile(r"^\([가나다라마바사아자차카타파하]\)\s")),
]
_RANK = {name: i for i, (name, _) in enumerate(_PATTERNS)}
_LEGAL = {"편", "장", "절", "관"}

_MAX_TITLE_LEN = 60
# 문장으로 끝나면 제목이 아니다 ("…했다", "…입니다.", "…함.")
# "요·음·함"은 마침표가 있을 때만 문장으로 본다 ("1. 개요"는 제목)
_SENTENCE_END = re.compile(r"다\.?$|(요|음|함|임|됨)\.$|[.!?。]$")


def heading_kind(text: str) -> str | None:
    """제목 모양이면 그 이름(예: '장', '숫자'), 아니면 None."""
    t = text.strip()
    if not t or len(t) > _MAX_TITLE_LEN or "\n" in t:
        return None
    for name, pat in _PATTERNS:
        if pat.match(t):
            body = pat.sub("", t, count=1).strip()
            if not body or _SENTENCE_END.search(body):
                return None
            return name
    return None


def _is_body(block: Block) -> bool:
    return block.get("locator", {}).get("kind", "paragraph") == "paragraph"


def apply_headings(blocks: list[Block]) -> list[Block]:
    """제목을 찾고(필요하면) 모든 블록의 heading_path를 채운다. 블록을 그 자리에서 고치고 그대로 돌려준다."""
    has_style_heading = any(b["type"] == "heading" for b in blocks)

    if not has_style_heading:
        found = [
            (b, kind)
            for b in blocks
            if b["type"] == "paragraph" and _is_body(b)
            and (kind := heading_kind(b.get("text", ""))) is not None
        ]
        # 법령 문서(편·장·절·관이 있음)에서 "1." "가."는 조 아래 호·목(목록)이지 제목이 아니다
        if any(kind in _LEGAL for _, kind in found):
            found = [(b, kind) for b, kind in found if kind in _LEGAL]
        present = sorted({kind for _, kind in found}, key=_RANK.__getitem__)
        level_of = {kind: i + 1 for i, kind in enumerate(present)}
        for b, kind in found:
            b["type"] = "heading"
            b["level"] = level_of[kind]
            b["heading_source"] = "pattern"

    stack: list[str] = []
    for b in blocks:
        if b["type"] == "heading":
            parent = stack[: b["level"] - 1]
            b["heading_path"] = list(parent)
            stack = parent + [b["text"]]
        else:
            b["heading_path"] = list(stack)
    return blocks
