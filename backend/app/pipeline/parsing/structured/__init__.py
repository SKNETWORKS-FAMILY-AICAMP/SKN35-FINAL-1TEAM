"""Structured parsers for modern Office files and text PDFs."""

from importlib import import_module
from pathlib import Path

from .base import DocumentParser, ParseError


_PARSERS = {"docx": "DocxParser", "pptx": "PptxParser", "pdf": "PdfParser", "xlsx": "XlsxParser"}


def __getattr__(name: str):
    # Keep package-level class imports available without loading every parser.
    for suffix, class_name in _PARSERS.items():
        if class_name == name:
            return getattr(import_module(f".{suffix}_parser", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def parser_for(path: str) -> DocumentParser:
    suffix = Path(path).suffix.lower().lstrip(".")
    class_name = _PARSERS.get(suffix)
    if class_name is None:
        raise ParseError(f"지원하지 않는 형식: {suffix!r}")
    module = import_module(f".{suffix}_parser", __name__)
    return getattr(module, class_name)()
