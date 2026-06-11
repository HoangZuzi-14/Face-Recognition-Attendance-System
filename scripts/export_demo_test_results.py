"""Export end-to-end real demo test evidence from the runtime database."""

import argparse
import csv
import sqlite3
from datetime import datetime
from pathlib import Path


EVENT_FIELDS = [
    "event_id",
    "student_db_key",
    "decision",
    "recognition_score",
    "liveness_score",
    "liveness_label",
    "attack_type",
    "timestamp",
    "attendance_logged",
    "spoof_attendance_violation",
]


def _table_exists(conn, table_name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(conn, table_name):
    if not _table_exists(conn, table_name):
        return set()
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})")}


def _select_expr(columns, column_name, fallback="NULL"):
    return column_name if column_name in columns else f"{fallback} AS {column_name}"


def _where_for_filter(since=None, demo_date=None, all_history=False):
    if all_history:
        return "", []
    if since:
        return "WHERE timestamp >= ?", [since]
    if demo_date:
        return "WHERE substr(timestamp, 1, 10) = ?", [demo_date]
    today = datetime.now().date().isoformat()
    return "WHERE substr(timestamp, 1, 10) = ?", [today]


def load_recognition_events(conn, since=None, demo_date=None, all_history=False):
    columns = _table_columns(conn, "recognition_events")
    if not columns:
        return []
    timestamp_expr = (
        "timestamp"
        if "timestamp" in columns
        else "created_at AS timestamp"
        if "created_at" in columns
        else "NULL AS timestamp"
    )
    where_clause, params = _where_for_filter(
        since=since,
        demo_date=demo_date,
        all_history=all_history,
    )
    query = f"""
        SELECT * FROM (
            SELECT
                {_select_expr(columns, "id")} AS event_id,
                {_select_expr(columns, "student_db_key")},
                {_select_expr(columns, "decision")},
                {_select_expr(columns, "recognition_score")},
                {_select_expr(columns, "liveness_score")},
                {_select_expr(columns, "liveness_label")},
                {_select_expr(columns, "attack_type")},
                {timestamp_expr}
            FROM recognition_events
        )
        {where_clause}
        ORDER BY event_id
    """
    conn.row_factory = sqlite3.Row
    return [dict(row) for row in conn.execute(query, params).fetchall()]


def load_attendance_keys(conn):
    columns = _table_columns(conn, "attendance")
    if not columns or "student_db_key" not in columns:
        return set(), 0
    rows = conn.execute("SELECT student_db_key FROM attendance").fetchall()
    keys = {row[0] for row in rows if row[0]}
    return keys, len(rows)


def _is_spoof_event(event):
    decision = str(event.get("decision") or "").upper()
    liveness_label = str(event.get("liveness_label") or "").upper()
    return decision == "REJECT_SPOOF" or liveness_label == "SPOOF"


def _missing_required_fields(event):
    missing = []
    for field in [
        "recognition_score",
        "liveness_score",
        "liveness_label",
        "decision",
        "timestamp",
    ]:
        if event.get(field) in (None, ""):
            missing.append(field)
    if _is_spoof_event(event) and event.get("attack_type") in (None, ""):
        missing.append("attack_type")
    return missing


def build_demo_rows(events, attendance_keys):
    rows = []
    missing = []
    violations = []
    for event in events:
        key = event.get("student_db_key") or ""
        attendance_logged = key in attendance_keys
        violation = _is_spoof_event(event) and attendance_logged
        row = {
            "event_id": event.get("event_id") or "",
            "student_db_key": key,
            "decision": event.get("decision") or "",
            "recognition_score": event.get("recognition_score") or "",
            "liveness_score": event.get("liveness_score") or "",
            "liveness_label": event.get("liveness_label") or "",
            "attack_type": event.get("attack_type") or "",
            "timestamp": event.get("timestamp") or "",
            "attendance_logged": "yes" if attendance_logged else "no",
            "spoof_attendance_violation": "yes" if violation else "no",
        }
        rows.append(row)

        missing_fields = _missing_required_fields(event)
        if missing_fields:
            missing.append(
                {
                    "event_id": row["event_id"],
                    "student_db_key": key,
                    "missing_fields": missing_fields,
                }
            )
        if violation:
            violations.append(key)
    return rows, missing, sorted(set(violations))


def _write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EVENT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(path, summary, rows):
    lines = [
        "# End-to-End Real Demo Test Results",
        "",
        f"- Recognition events: {summary['recognition_events']}",
        f"- Attendance rows: {summary['attendance_rows']}",
        f"- Spoof attendance violations: {len(summary['spoof_attendance_violations'])}",
        f"- Events missing required fields: {len(summary['events_missing_required_fields'])}",
        f"- Filter since: {summary['filter']['since'] or ''}",
        f"- Filter date: {summary['filter']['demo_date'] or 'today'}",
        f"- All history: {summary['filter']['all_history']}",
        "",
        "## Required Event Fields",
        "",
        "- recognition_score",
        "- liveness_score",
        "- liveness_label",
        "- attack_type for spoof events",
        "- decision",
        "- timestamp",
        "",
        "## Spoof Attendance Check",
        "",
    ]
    if summary["spoof_attendance_violations"]:
        lines.append("Spoof attack events were logged as attendance for:")
        lines.extend(f"- {key}" for key in summary["spoof_attendance_violations"])
    else:
        lines.append("No spoof attack event was found in attendance.")

    lines.extend(["", "## Missing Required Fields", ""])
    if summary["events_missing_required_fields"]:
        for item in summary["events_missing_required_fields"]:
            missing = ", ".join(item["missing_fields"])
            lines.append(
                f"- event_id={item['event_id']} student_db_key={item['student_db_key']}: {missing}"
            )
    else:
        lines.append("No recognition event is missing required demo fields.")

    lines.extend(
        [
            "",
            "## Event Rows",
            "",
            "| event_id | student_db_key | decision | recognition_score | liveness_score | liveness_label | attack_type | timestamp | attendance_logged | spoof_violation |",
            "| --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        lines.append(
            "| {event_id} | {student_db_key} | {decision} | {recognition_score} | "
            "{liveness_score} | {liveness_label} | {attack_type} | {timestamp} | "
            "{attendance_logged} | {spoof_attendance_violation} |".format(**row)
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def export_demo_test_results(
    db_path="app/attendance.db",
    reports_dir="reports",
    since=None,
    demo_date=None,
    all_history=False,
):
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        events = load_recognition_events(
            conn,
            since=since,
            demo_date=demo_date,
            all_history=all_history,
        )
        attendance_keys, attendance_count = load_attendance_keys(conn)
    finally:
        conn.close()

    rows, missing, violations = build_demo_rows(events, attendance_keys)
    summary = {
        "recognition_events": len(events),
        "attendance_rows": attendance_count,
        "spoof_attendance_violations": violations,
        "events_missing_required_fields": missing,
        "filter": {
            "since": since,
            "demo_date": demo_date,
            "all_history": all_history,
        },
    }

    _write_csv(reports_dir / "demo_test_results.csv", rows)
    _write_markdown(reports_dir / "demo_test_results.md", summary, rows)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Export Face_attendance end-to-end demo test evidence."
    )
    parser.add_argument("--db", default="app/attendance.db")
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--since", default=None, help="Export events at or after this ISO timestamp.")
    parser.add_argument("--date", dest="demo_date", default=None, help="Export events for YYYY-MM-DD.")
    parser.add_argument("--all-history", action="store_true", help="Export all historical events.")
    args = parser.parse_args(argv)

    summary = export_demo_test_results(
        args.db,
        args.reports_dir,
        since=args.since,
        demo_date=args.demo_date,
        all_history=args.all_history,
    )
    print(f"Recognition events: {summary['recognition_events']}")
    print(f"Attendance rows: {summary['attendance_rows']}")
    print(f"Spoof attendance violations: {len(summary['spoof_attendance_violations'])}")
    print(f"Events missing required fields: {len(summary['events_missing_required_fields'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
