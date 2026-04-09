
from __future__ import annotations

import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TARGET = DATA_DIR / "question_bank.json"
SOURCE = DATA_DIR / "questions_import.csv"


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "si", "sí", "yes"}


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"No existe {SOURCE}. Usa data/questions_import_template.csv como base.")
    rows = []
    with open(SOURCE, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            options = {
                key: row[col].strip()
                for key, col in [("A", "option_a"), ("B", "option_b"), ("C", "option_c"), ("D", "option_d"), ("E", "option_e")]
                if row.get(col, "").strip()
            }
            rows.append(
                {
                    "id": row["id"].strip(),
                    "subject_code": row["subject_code"].strip(),
                    "subject_label": row["subject_label"].strip(),
                    "group": row["group"].strip(),
                    "track": row.get("track", "").strip() or None,
                    "exam_form": row["exam_form"].strip(),
                    "source_exam": row["source_exam"].strip(),
                    "question_number": int(row["question_number"]),
                    "context_id": row.get("context_id", "").strip() or None,
                    "topic": row.get("topic", "").strip() or "pendiente_de_etiquetar",
                    "skill": json.loads(row.get("skill_json", "[]") or "[]"),
                    "stem": row["stem"].strip(),
                    "options": options,
                    "correct_option": row["correct_option"].strip(),
                    "is_scored": parse_bool(row.get("is_scored", "true")),
                    "is_deleted": parse_bool(row.get("is_deleted", "false")),
                    "delivery_mode": row.get("delivery_mode", "text").strip() or "text",
                    "active": parse_bool(row.get("active", "true")),
                }
            )
    TARGET.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Banco actualizado: {TARGET} ({len(rows)} preguntas)")


if __name__ == "__main__":
    main()
