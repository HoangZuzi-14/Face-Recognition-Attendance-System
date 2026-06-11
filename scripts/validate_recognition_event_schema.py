"""Validate recognition_events schema for liveness analytics."""

import argparse
import sqlite3
from dataclasses import dataclass


REQUIRED_COLUMNS = [
    "id",
    "class_id",
    "session_id",
    "student_db_key",
    "decision",
    "confidence",
    "distance",
    "gap",
    "created_at",
    "liveness_score",
    "liveness_label",
    "attack_type",
    "liveness_reasons",
    "recognition_score",
]


@dataclass(frozen=True)
class SchemaValidationResult:
    ok: bool
    missing_columns: list[str]


def validate_schema(db_path="app/attendance.db"):
    conn = sqlite3.connect(db_path)
    try:
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(recognition_events)")
        }
    finally:
        conn.close()
    missing = [column for column in REQUIRED_COLUMNS if column not in columns]
    return SchemaValidationResult(ok=not missing, missing_columns=missing)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate recognition_events liveness schema."
    )
    parser.add_argument("--db", default="app/attendance.db")
    args = parser.parse_args(argv)

    result = validate_schema(args.db)
    print(f"Recognition event schema OK: {result.ok}")
    if result.missing_columns:
        print("Missing columns:")
        for column in result.missing_columns:
            print(f"- {column}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
