"""Match PowerPoint title shapes to Docling text items."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from statistics import median

from docling_core.types.doc import DocItemLabel, TextItem
from docling_core.types.doc.common.content_layer import ContentLayer
from pptx import Presentation
from pptx.enum.shapes import PP_PLACEHOLDER


_TITLE_TYPES = {PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE, PP_PLACEHOLDER.VERTICAL_TITLE}
_CHROME_TYPES = {PP_PLACEHOLDER.FOOTER, PP_PLACEHOLDER.DATE, PP_PLACEHOLDER.SLIDE_NUMBER}


@dataclass
class _Candidate:
    slide: int
    left: float
    top: float
    right: float
    bottom: float
    size: float
    bold: bool
    explicit: bool
    items: list[TextItem]

    @property
    def normalized_text(self) -> str:
        return " ".join(" ".join(item.text.split()) for item in self.items).casefold()


def _same_layout(left: _Candidate, right: _Candidate) -> bool:
    return (
        abs(left.left - right.left) <= 0.035
        and abs(left.top - right.top) <= 0.035
        and abs(left.right - right.right) <= 0.08
        and (not left.size or not right.size or abs(left.size - right.size) <= 2)
        and left.bold == right.bold
    )


def _layout_repeats(candidate: _Candidate, peers: list[_Candidate]) -> tuple[bool, bool]:
    repeated_slides = {
        peer.slide for peer in peers if peer.normalized_text == candidate.normalized_text
    }
    changing_slides = {
        peer.slide for peer in peers if peer.normalized_text != candidate.normalized_text
    }
    return bool(repeated_slides and len(repeated_slides) >= len(changing_slides)), bool(changing_slides)


def _title_score(candidate, has_template, slide_candidates, other_tops) -> int:
    other_sizes = [item.size for item in slide_candidates if item is not candidate and item.size]
    body_size = median(other_sizes) if other_sizes else 18.0
    prominent = candidate.size >= 1.2 * body_size
    other_content = [
        item.top for item in slide_candidates if item is not candidate
    ] + other_tops
    before_content = bool(other_content) and candidate.top < min(other_content) - 0.015
    isolated = before_content and candidate.bottom <= min(other_content) - 0.015
    centered = (
        not other_content
        and abs((candidate.left + candidate.right) / 2 - 0.5) <= 0.2
        and 0.25 <= (candidate.top + candidate.bottom) / 2 <= 0.7
    )
    layout_score = 2 if isolated or centered else int(before_content)
    style_score = 2 if prominent else int(candidate.bold)
    template_score = 2 if has_template else 0
    if not layout_score or not (style_score or template_score):
        return 0
    # Top placement and bold alone are weak cues. An isolated, centered
    # section slide can be identified by its layout and its bold text.
    return layout_score + style_score + template_score + int(centered and candidate.bold)


def pptx_headings(path: str, doc) -> dict[str, str]:
    """Map each title's first item to its text and subsequent items to an empty string."""
    presentation = Presentation(path)
    slide_width, slide_height = presentation.slide_width, presentation.slide_height
    items_by_box = defaultdict(list)
    for item in doc.texts:
        if item.content_layer != ContentLayer.BODY or not item.prov or not item.text.strip():
            continue
        prov = item.prov[0]
        box = prov.bbox.to_top_left_origin(slide_height)
        items_by_box[(prov.page_no, box.l, box.t, box.r, box.b)].append(item)

    candidates_by_slide: dict[int, list[_Candidate]] = defaultdict(list)
    other_tops: dict[int, list[float]] = defaultdict(list)
    for slide_number, slide in enumerate(presentation.slides, start=1):
        shapes = [
            shape for shape in slide.shapes
            if shape.has_text_frame and shape.text.strip()
            and (not shape.is_placeholder or shape.placeholder_format.type not in _CHROME_TYPES)
            and None not in (shape.left, shape.top, shape.width, shape.height)
        ]
        boxes = [
            (slide_number, shape.left, shape.top, shape.left + shape.width, shape.top + shape.height)
            for shape in shapes
        ]
        box_counts = Counter(boxes)
        other_tops[slide_number].extend(
            shape.top / slide_height for shape in slide.shapes
            if shape.has_table and shape.top is not None
        )
        for shape, box in zip(shapes, boxes):
            items = items_by_box.get(box, ())
            if box_counts[box] != 1 or not items or any(
                item.label not in (DocItemLabel.TITLE, DocItemLabel.PARAGRAPH) for item in items
            ):
                other_tops[slide_number].append(shape.top / slide_height)
                continue
            is_title = shape.is_placeholder and shape.placeholder_format.type in _TITLE_TYPES
            sizes = Counter()
            total = bold = 0
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    length = len(run.text.strip())
                    size = run.font.size or paragraph.font.size
                    if size and length:
                        sizes[size.pt] += length
                    total += length
                    if run.font.bold is True or (run.font.bold is None and paragraph.font.bold is True):
                        bold += length
            font_size = sizes.most_common(1)[0][0] if sizes else 0
            _, left, top, right, bottom = box
            candidates_by_slide[slide_number].append(_Candidate(
                slide_number, left / slide_width, top / slide_height,
                right / slide_width, bottom / slide_height,
                font_size, total > 0 and bold * 2 >= total, is_title, items,
            ))

    headings = {}
    all_candidates = [candidate for candidates in candidates_by_slide.values() for candidate in candidates]
    for slide_number, candidates in candidates_by_slide.items():
        selected = [candidate for candidate in candidates if candidate.explicit]
        if not selected:
            eligible = []
            for candidate in candidates:
                peers = [
                    peer for peer in all_candidates
                    if peer.slide != slide_number and _same_layout(candidate, peer)
                ]
                repeated, has_template = _layout_repeats(candidate, peers)
                if not repeated:
                    eligible.append((candidate, has_template))
            slide_content = [candidate for candidate, _ in eligible]
            scores = [
                (_title_score(candidate, has_template, slide_content, other_tops[slide_number]), candidate)
                for candidate, has_template in eligible
            ]
            scores.sort(key=lambda pair: pair[0], reverse=True)
            if scores and scores[0][0] >= 4 and (len(scores) == 1 or scores[0][0] > scores[1][0]):
                selected = [scores[0][1]]

        for candidate in selected:
            items = candidate.items
            first, *remaining = items
            headings[first.self_ref] = "\n".join(item.text.strip() for item in items)
            headings.update((item.self_ref, "") for item in remaining)
    return headings
