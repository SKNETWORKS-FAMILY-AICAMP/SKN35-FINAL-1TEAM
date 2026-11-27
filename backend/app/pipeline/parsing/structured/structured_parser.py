import argparse
import json
import sys
from dataclasses import asdict

from .docling_parser import _numbered_reference_text
from . import parser_for


def main():
    cli = argparse.ArgumentParser(description="DOCX / PPTX / PDF / XLSX 구조 추출")
    cli.add_argument("path", help="원본 파일")
    args = cli.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    result = parser_for(args.path).parse(args.path)
    payload = asdict(result)
    numbers = {block.location.table_key: block.table_number for block in result.blocks if block.kind.is_table}
    for block, item in zip(result.blocks, payload["blocks"]):
        item["table_reference_text"] = _numbered_reference_text(block, numbers)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
