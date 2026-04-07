import sqlite3
import pandas as pd
from datetime import datetime, time
import os

DB_PATH = "app/attendance.db"


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY,
            class_name TEXT UNIQUE,
            created_at TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY,
            mssv TEXT UNIQUE,
            full_name TEXT,
            db_key TEXT DEFAULT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS class_students (
            class_id INTEGER,
            student_id INTEGER,
            FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            PRIMARY KEY (class_id, student_id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY,
            student_db_key TEXT,
            class_id INTEGER,
            date TEXT,
            timestamp TEXT,
            confidence REAL,
            status TEXT,
            UNIQUE(student_db_key, class_id, date)
        )
    ''')

    conn.commit()
    conn.close()


# --------------- Class CRUD ---------------

def create_class(class_name):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO classes (class_name, created_at) VALUES (?, ?)",
                  (class_name, datetime.now().isoformat()))
        conn.commit()
        class_id = c.lastrowid
    except sqlite3.IntegrityError:
        class_id = None
    conn.close()
    return class_id


def get_classes():
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, class_name, created_at FROM classes ORDER BY class_name", conn)
    conn.close()
    return df


def delete_class(class_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM class_students WHERE class_id=?", (class_id,))
    c.execute("DELETE FROM attendance WHERE class_id=?", (class_id,))
    c.execute("DELETE FROM classes WHERE id=?", (class_id,))
    conn.commit()
    conn.close()


# --------------- Student / Roster ---------------

def upload_roster(class_id, df, existing_faces=None):
    """Import roster from DataFrame with columns 'MSSV' and 'FullName'.
    Returns (added_count, skipped_count).
    """
    if existing_faces is None:
        existing_faces = set()
        
    conn = get_connection()
    c = conn.cursor()
    added = 0
    skipped = 0

    for _, row in df.iterrows():
        mssv = str(row.get("MSSV", "")).strip()
        # Fallback to 'Họ và Tên' in case they still use the old template
        full_name = str(row.get("FullName", row.get("Họ và Tên", ""))).strip()

        if not mssv or not full_name:
            skipped += 1
            continue

        assumed_db_key = full_name.replace(" ", "_")
        db_key_to_set = assumed_db_key if assumed_db_key in existing_faces else None

        # Insert or update student (to allow correcting names in roster)
        c.execute("""
            INSERT INTO students (mssv, full_name, db_key) 
            VALUES (?, ?, ?)
            ON CONFLICT(mssv) DO UPDATE SET full_name = EXCLUDED.full_name
        """, (mssv, full_name, db_key_to_set))
        
        # If we successfully found a key (e.g. from existing face data), 
        # ensure it's linked
        if db_key_to_set:
            c.execute("UPDATE students SET db_key=? WHERE mssv=?", (db_key_to_set, mssv))

        # Get student_id
        c.execute("SELECT id FROM students WHERE mssv=?", (mssv,))
        student_id = c.fetchone()[0]

        # Link to class
        c.execute("INSERT OR IGNORE INTO class_students (class_id, student_id) VALUES (?, ?)",
                  (class_id, student_id))
        added += 1

    conn.commit()
    conn.close()
    return added, skipped


def get_class_roster(class_id):
    """Get all students in a class."""
    conn = get_connection()
    query = '''
        SELECT s.mssv, s.full_name, s.db_key
        FROM students s
        JOIN class_students cs ON s.id = cs.student_id
        WHERE cs.class_id = ?
        ORDER BY s.full_name
    '''
    df = pd.read_sql_query(query, conn, params=(class_id,))
    conn.close()
    return df


def get_all_students():
    """Get all students."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, mssv, full_name, db_key FROM students ORDER BY full_name", conn)
    conn.close()
    return df


def link_student_face(mssv, db_key):
    """Link a student MSSV to a face database key."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE students SET db_key=? WHERE mssv=?", (db_key, mssv))
    conn.commit()
    conn.close()


def get_student_by_db_key(db_key):
    """Get student info from face db key."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT mssv, full_name FROM students WHERE db_key=?", (db_key,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"mssv": row[0], "full_name": row[1]}
    return None


# --------------- Attendance ---------------

def log_attendance(db_key, class_id, confidence, deadline_hour=8, deadline_minute=0):
    """Log attendance for a student. Only once per class per day.
    Returns (logged: bool, status: str).
    """
    conn = get_connection()
    c = conn.cursor()

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    # Check if already attended today for this class
    c.execute("SELECT id FROM attendance WHERE student_db_key=? AND class_id=? AND date=?",
              (db_key, class_id, today))
    if c.fetchone() is not None:
        conn.close()
        return False, None  # Already attended

    # Determine status based on deadline
    deadline = time(hour=deadline_hour, minute=deadline_minute).isoformat()
    current_time = now.time().isoformat()
    status = "PRESENT" if current_time <= deadline else "LATE"

    c.execute("""INSERT INTO attendance (student_db_key, class_id, date, timestamp, confidence, status)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (db_key, class_id, today, now.isoformat(), confidence, status))
    conn.commit()
    conn.close()
    return True, status


def get_attended_today_for_class(class_id):
    """Get set of db_keys that already attended today for a class."""
    conn = get_connection()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT student_db_key FROM attendance WHERE class_id=? AND date=?",
              (class_id, today))
    attended = {row[0] for row in c.fetchall()}
    conn.close()
    return attended


def get_full_attendance(class_id, deadline_hour=8, deadline_minute=0):
    """Get full class roster with attendance status.
    Returns DataFrame with: MSSV, Họ và Tên, Thời Gian, Trạng Thái
    """
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")

    query = '''
        SELECT
            s.mssv AS "MSSV",
            s.full_name AS "Họ và Tên",
            s.db_key,
            a.timestamp,
            a.status
        FROM students s
        JOIN class_students cs ON s.id = cs.student_id
        LEFT JOIN attendance a ON a.student_db_key = s.db_key
                                AND a.class_id = ?
                                AND a.date = ?
        WHERE cs.class_id = ?
        ORDER BY s.full_name
    '''
    df = pd.read_sql_query(query, conn, params=(class_id, today, class_id))
    conn.close()

    # Build display columns
    rows = []
    from datetime import time
    deadline_time = time(hour=deadline_hour, minute=deadline_minute)
    
    for _, row in df.iterrows():
        mssv = row["MSSV"]
        name = row["Họ và Tên"]
        db_key = row["db_key"]

        if db_key is None or db_key == "":
            status = "UNKNOWN"
            time_str = "--:--:--"
        elif row["timestamp"] is None:
            status = "ABSENT"
            time_str = "--:--:--"
        else:
            try:
                ts = datetime.fromisoformat(row["timestamp"])
                time_str = ts.strftime("%H:%M:%S")
                # Dynamically calculate status instead of relying purely on DB
                if ts.time() <= deadline_time:
                    status = "PRESENT"
                else:
                    status = "LATE"
            except Exception:
                time_str = "--:--:--"
                status = row["status"]

        rows.append({
            "MSSV": mssv,
            "Họ và Tên": name,
            "Thời Gian": time_str,
            "Trạng Thái": status
        })

    return pd.DataFrame(rows)


def get_today_log_for_class(class_id):
    """Get only attended records for today (simple log)."""
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    query = """SELECT student_db_key, timestamp, confidence, status
               FROM attendance WHERE class_id=? AND date=?"""
    df = pd.read_sql_query(query, conn, params=(class_id, today))
    conn.close()
    return df


def export_csv(class_id=None, export_path="app/attendance_export.csv"):
    conn = get_connection()
    if class_id:
        today = datetime.now().strftime("%Y-%m-%d")
        query = '''
            SELECT s.mssv, s.full_name, a.timestamp, a.confidence, a.status
            FROM attendance a
            LEFT JOIN students s ON a.student_db_key = s.db_key
            WHERE a.class_id = ? AND a.date = ?
        '''
        df = pd.read_sql_query(query, conn, params=(class_id, today))
    else:
        df = pd.read_sql_query("SELECT * FROM attendance", conn)
    df.to_csv(export_path, index=False)
    conn.close()
    return export_path


def clear_attendance(class_id=None):
    conn = get_connection()
    c = conn.cursor()
    if class_id:
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("DELETE FROM attendance WHERE class_id=? AND date=?", (class_id, today))
    else:
        c.execute("DELETE FROM attendance")
    conn.commit()
    conn.close()


init_db()
