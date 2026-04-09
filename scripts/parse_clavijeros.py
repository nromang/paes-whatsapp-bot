
from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader


def parse_clavijero(pdf_path: Path) -> dict:
    reader = PdfReader(str(pdf_path))
    page3 = reader.pages[2].extract_text() or ""
    page5 = reader.pages[4].extract_text() or ""
    key_matches = re.findall(r'(\d+)(\*\*|\*)?\s+([A-E])', page3)
    keys = {}
    excluded = []
    for num, marker, key in key_matches:
        n = int(num)
        keys[n] = key
        if marker == "*":
            excluded.append(n)
    deleted = sorted({int(n) for n in re.findall(r'(\d+)\*\*', page3)})
    table_matches = re.findall(r'(\d+)\s+(\d+)', page5)
    table = {int(p): int(score) for p, score in table_matches if int(p) <= 100}
    return {
        "keys": keys,
        "excluded_questions": sorted(excluded),
        "deleted_questions": deleted,
        "paes_table": table,
        "valid_question_count": max(table.keys()) if table else None,
    }


def main() -> None:
    data_dir = Path(__file__).resolve().parent.parent / "data"
    for pdf_path in sorted(data_dir.glob("*clavijero*.pdf")):
        parsed = parse_clavijero(pdf_path)
        out = pdf_path.with_suffix(".parsed.json")
        out.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Creado {out.name}")


if __name__ == "__main__":
    main()
