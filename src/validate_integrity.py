import argparse
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.integrity import validate_integrity


def main():
    parser = argparse.ArgumentParser(
        description="Validate synchronization between SQLite, face DB, and image folders."
    )
    parser.add_argument("--sql-db", default="app/attendance.db")
    parser.add_argument("--face-db", default="data/embeddings/db.pkl")
    parser.add_argument("--raw-dir", default="data/raw")
    parser.add_argument("--processed-dir", default="data/processed")
    parser.add_argument("--max-items", type=int, default=50, help="Maximum items to print per section.")
    parser.add_argument("--all", action="store_true", help="Print every item in every section.")
    args = parser.parse_args()

    report = validate_integrity(
        sql_db_path=args.sql_db,
        face_db_path=args.face_db,
        raw_dir=args.raw_dir,
        processed_dir=args.processed_dir,
    )

    max_items = None if args.all else args.max_items
    for line in report.to_lines(max_items=max_items):
        print(line)

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
