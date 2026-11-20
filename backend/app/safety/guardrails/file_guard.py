"""입력 가드레일 - 파일 검증 (구현계획서 5-1). modules/documents 가 업로드 직후 호출한다."""

import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GuardConfig:
    max_file_bytes: int = 20 * 1024 * 1024
    max_zip_entries: int = 2_000
    max_zip_uncompressed_bytes: int = 200 * 1024 * 1024
    max_zip_ratio: int = 100
    pdf_sample_pages: int = 10
    pdf_min_chars_per_page: int = 20


@dataclass(frozen=True)
class GuardResult:
    ok: bool
    code: str | None = None
    reason: str | None = None
    extension: str | None = None
    sha256: str | None = None
    notices: tuple[str, ...] = ()


# 확장자별 내부 필수 파일 (zip 계열)
ZIP_REQUIRED = {
    ".docx": "word/document.xml",
    ".pptx": "ppt/presentation.xml",
    ".xlsx": "xl/workbook.xml",
    ".hwpx": "Contents/header.xml",
}
TEXT_EXTS = {".md", ".txt"}
OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # 구형 HWP/Office
IMAGES = (b"\x89PNG", b"\xff\xd8\xff", b"GIF8", b"BM", b"II*\x00", b"MM\x00*")
PDF_RISKY = (b"/JavaScript", b"/JS", b"/Launch")


def _fail(code: str, reason: str, ext: str | None = None) -> GuardResult:
    return GuardResult(False, code, reason, ext)


def _check_zip(p: Path, ext: str, cfg: GuardConfig) -> GuardResult | None:
    try:
        with zipfile.ZipFile(p) as zf:
            infos = zf.infolist()
            if len(infos) > cfg.max_zip_entries:
                return _fail("ZIP_TOO_MANY_ENTRIES", "압축 내부 파일 수가 너무 많습니다.", ext)
            if sum(i.file_size for i in infos) > cfg.max_zip_uncompressed_bytes or any(
                i.compress_size and i.file_size / i.compress_size > cfg.max_zip_ratio for i in infos
            ):
                return _fail("ZIP_BOMB", "압축 폭탄으로 의심되는 파일입니다.", ext)
            if any(i.filename.lower().endswith("vbaproject.bin") for i in infos):
                return _fail("MACRO_DETECTED", "매크로가 포함된 파일은 제출할 수 없습니다.", ext)
            if ZIP_REQUIRED[ext] not in zf.namelist():
                return _fail("MAGIC_MISMATCH", "파일 구조가 확장자와 맞지 않습니다.", ext)
    except zipfile.BadZipFile:
        return _fail("CORRUPT_FILE", "손상되었거나 올바른 형식이 아닌 파일입니다.", ext)


def _check_pdf(p: Path, ext: str, cfg: GuardConfig) -> GuardResult | None:
    if any(t in p.read_bytes() for t in PDF_RISKY):
        return _fail("PDF_ACTIVE_CONTENT", "스크립트나 실행 동작이 포함된 PDF는 제출할 수 없습니다.", ext)

    import pypdfium2 as pdfium  # docling 의존성, 지연 import

    try:
        pdf = pdfium.PdfDocument(str(p))
    except Exception:
        return _fail("CORRUPT_FILE", "PDF를 열 수 없습니다.", ext)
    try:
        n = min(len(pdf), cfg.pdf_sample_pages)
        chars = sum(len(pdf[i].get_textpage().get_text_range().strip()) for i in range(n))
        if n == 0 or chars / n < cfg.pdf_min_chars_per_page:
            return _fail("SCANNED_PDF", "글자를 추출할 수 없는 스캔 PDF입니다. 텍스트 PDF로 제출해 주세요.", ext)
    finally:
        pdf.close()


def _check_text(p: Path, ext: str) -> GuardResult | None:
    data = p.read_bytes()
    if b"\x00" in data[:8192]:
        return _fail("NOT_TEXT", "텍스트 파일이 아닙니다.", ext)
    for enc in ("utf-8-sig", "cp949"):
        try:
            data.decode(enc)
            return None
        except UnicodeDecodeError:
            pass
    return _fail("BAD_ENCODING", "UTF-8 또는 CP949로 저장해 주세요.", ext)


def validate_upload(path: str | Path, original_filename: str, cfg: GuardConfig = GuardConfig()) -> GuardResult:
    """실패 시 즉시 사유를 돌려준다. path: 임시 저장 경로, original_filename: 확장자 판단용."""
    p, ext = Path(path), Path(original_filename).suffix.lower()

    if ext == ".hwp":
        return _fail("LEGACY_HWP", "구형 HWP는 제출할 수 없습니다. HWPX로 저장해 주세요.", ext)
    if ext not in ZIP_REQUIRED and ext not in TEXT_EXTS and ext != ".pdf":
        return _fail("EXT_NOT_ALLOWED", "허용되지 않는 확장자입니다.", ext)

    size = p.stat().st_size
    if size == 0:
        return _fail("EMPTY_FILE", "빈 파일입니다.", ext)
    if size > cfg.max_file_bytes:
        return _fail("TOO_LARGE", f"파일 크기가 {cfg.max_file_bytes // 1024 // 1024}MB를 넘습니다.", ext)

    with p.open("rb") as f:
        head = f.read(16)
    if head.startswith(OLE):
        return _fail("LEGACY_OLE", "구형 Office/HWP 형식은 제출할 수 없습니다.", ext)
    if ext not in TEXT_EXTS and head.startswith(IMAGES):
        return _fail("IMAGE_REJECTED", "이미지 파일은 제출할 수 없습니다.", ext)
    if (ext == ".pdf" and not head.startswith(b"%PDF-")) or (ext in ZIP_REQUIRED and not head.startswith(b"PK\x03\x04")):
        return _fail("MAGIC_MISMATCH", "파일 내용이 확장자와 다릅니다.", ext)

    failed = (
        _check_zip(p, ext, cfg) if ext in ZIP_REQUIRED
        else _check_pdf(p, ext, cfg) if ext == ".pdf"
        else _check_text(p, ext)
    )
    if failed:
        return failed

    notices = ("XLSX는 표 구조상 변경 감지 정확도가 낮을 수 있습니다.",) if ext == ".xlsx" else ()
    return GuardResult(True, extension=ext, sha256=hashlib.file_digest(p.open("rb"), "sha256").hexdigest(), notices=notices)
