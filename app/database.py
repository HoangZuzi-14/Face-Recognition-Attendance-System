import sqlite3
import pandas as pd
from datetime import datetime, time
import os
import json
from app.backup import backup_sqlite_db

DB_PATH = "app/attendance.db"
DEFAULT_CLASS_NAME = "Default Demo Class"
DEFAULT_ROSTER = [
    ("DEMO002", "Nguyen Khanh Toan"),
    ("DEMO003", "Tony Blair"),
    ("DEMO004", "Donald Rumsfeld"),
    ("DEMO005", "Gerhard Schroeder"),
    ("DEMO006", "Ariel Sharon"),
    ("DEMO007", "Hugo Chavez"),
    ("DEMO008", "Junichiro Koizumi"),
    ("DEMO009", "Jean Chretien"),
    ("DEMO010", "John Ashcroft"),
    ("DEMO011", "Bill Clinton"),
    ("DEMO012", "Bill Gates"),
    ("DEMO013", "Tom Cruise"),
    ("DEMO014", "Tom Hanks"),
    ("DEMO015", "Brad Pitt"),
    ("DEMO016", "Angelina Jolie"),
    ("DEMO017", "Jennifer Aniston"),
    ("DEMO018", "Serena Williams"),
    ("DEMO019", "Roger Federer"),
    ("DEMO020", "Tiger Woods"),
    ("DEMO021", "David Beckham"),
    ("DEMO022", "Michael Jordan"),
    ("DEMO023", "Barack Obama"),
    ("DEMO024", "Hillary Clinton"),
    ("DEMO025", "Donald Trump"),
    ("DEMO026", "Vladimir Putin"),
    ("DEMO027", "Angela Merkel"),
    ("DEMO028", "Elon Musk"),
    ("DEMO029", "Mark Zuckerberg"),
    ("DEMO030", "Taylor Swift"),
]


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
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_active INTEGER DEFAULT 1
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

    c.execute('''
        CREATE TABLE IF NOT EXISTS face_identities (
            id INTEGER PRIMARY KEY,
            student_id INTEGER,
            person_key TEXT UNIQUE,
            embedding_store TEXT DEFAULT 'db.pkl',
            active INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE SET NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance_sessions (
            id INTEGER PRIMARY KEY,
            class_id INTEGER,
            session_date TEXT,
            session_name TEXT,
            start_time TEXT,
            end_time TEXT,
            deadline_hour INTEGER,
            deadline_minute INTEGER,
            created_at TEXT,
            UNIQUE(class_id, session_date, session_name),
            FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY,
            action TEXT,
            entity_type TEXT,
            entity_id TEXT,
            actor TEXT,
            details TEXT,
            created_at TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS recognition_events (
            id INTEGER PRIMARY KEY,
            class_id INTEGER,
            session_id INTEGER,
            student_db_key TEXT,
            decision TEXT,
            confidence REAL,
            distance REAL,
            gap REAL,
            created_at TEXT,
            FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
            FOREIGN KEY (session_id) REFERENCES attendance_sessions(id) ON DELETE SET NULL
        )
    ''')

    _ensure_column(c, "attendance", "session_id", "INTEGER")
    _ensure_column(c, "attendance", "student_id", "INTEGER")
    _ensure_column(c, "attendance", "review_reason", "TEXT")
    _ensure_column(c, "audit_logs", "actor_user_id", "INTEGER")
    _ensure_column(c, "audit_logs", "actor_username", "TEXT")
    _ensure_column(c, "audit_logs", "target", "TEXT")
    _ensure_column(c, "audit_logs", "timestamp", "TEXT")
    _ensure_column(c, "audit_logs", "status", "TEXT DEFAULT 'SUCCESS'")
    _ensure_column(c, "recognition_events", "liveness_score", "REAL")
    _ensure_column(c, "recognition_events", "liveness_label", "TEXT")
    _ensure_column(c, "recognition_events", "attack_type", "TEXT")
    _ensure_column(c, "recognition_events", "liveness_reasons", "TEXT")
    _ensure_column(c, "recognition_events", "recognition_score", "REAL")
    _ensure_column(c, "recognition_events", "live_score", "REAL")
    _ensure_column(c, "recognition_events", "print_score", "REAL")
    _ensure_column(c, "recognition_events", "replay_score", "REAL")
    _ensure_column(c, "recognition_events", "spoof_score", "REAL")
    _ensure_column(c, "recognition_events", "attendance_logged", "INTEGER DEFAULT 0")

    _seed_default_users(conn)

    conn.commit()
    _sync_face_identities(conn)
    conn.close()

    try:
        class_id = ensure_default_class()
        ensure_default_roster(class_id)
    except Exception as e:
        print(f"Error seeding default demo data: {e}")


def _ensure_column(cursor, table_name, column_name, column_type):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = {row[1] for row in cursor.fetchall()}
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def _upsert_default_user(cursor, username, password, role):
    cursor.execute("SELECT id FROM users WHERE username=?", (username,))
    if cursor.fetchone():
        return
    from app.auth import hash_password

    cursor.execute(
        """
        INSERT INTO users (username, password_hash, role, created_at, is_active)
        VALUES (?, ?, ?, ?, 1)
        """,
        (username, hash_password(password), role, datetime.now().isoformat()),
    )


def _seed_default_users(conn):
    cursor = conn.cursor()

    from app.auth import ROLE_ADMIN, ROLE_TEACHER

    admin_username = os.environ.get("ATTENDANCE_ADMIN_USERNAME", "admin").strip() or "admin"
    admin_password = os.environ.get("ATTENDANCE_ADMIN_PASSWORD", "admin123").strip()
    if not admin_password:
        admin_password = "admin123"

    teacher_username = os.environ.get("ATTENDANCE_TEACHER_USERNAME", "teacher").strip() or "teacher"
    teacher_password = os.environ.get("ATTENDANCE_TEACHER_PASSWORD", "teacher123").strip()
    if not teacher_password:
        teacher_password = "teacher123"

    _upsert_default_user(cursor, admin_username, admin_password, ROLE_ADMIN)
    _upsert_default_user(cursor, teacher_username, teacher_password, ROLE_TEACHER)


def _sync_face_identities(conn):
    now = datetime.now().isoformat()
    conn.execute(
        """
        INSERT INTO face_identities (student_id, person_key, created_at, updated_at)
        SELECT id, db_key, ?, ?
        FROM students
        WHERE db_key IS NOT NULL AND TRIM(db_key) != ''
        ON CONFLICT(person_key) DO UPDATE SET
            student_id = excluded.student_id,
            active = 1,
            updated_at = excluded.updated_at
        """,
        (now, now),
    )
    conn.commit()


def _audit_target(entity_type=None, entity_id=None, target=None):
    if target:
        return str(target)
    if entity_type and entity_id is not None:
        return f"{entity_type}:{entity_id}"
    if entity_type:
        return str(entity_type)
    if entity_id is not None:
        return str(entity_id)
    return None


def _resolve_audit_actor(actor, actor_user_id, actor_username):
    if actor_user_id is None and actor_username is None and actor in (None, "system"):
        from app.audit_context import get_current_actor

        actor_user_id, actor_username = get_current_actor()
    if actor_username is None:
        actor_username = actor or "system"
    return actor_user_id, actor_username, actor_username


def write_audit_log(
    action,
    entity_type=None,
    entity_id=None,
    actor="system",
    details=None,
    actor_user_id=None,
    actor_username=None,
    target=None,
    status="SUCCESS",
):
    conn = get_connection()
    c = conn.cursor()
    timestamp = datetime.now().isoformat()
    actor_user_id, actor_username, legacy_actor = _resolve_audit_actor(
        actor, actor_user_id, actor_username
    )
    target = _audit_target(entity_type, entity_id, target)
    c.execute(
        """
        INSERT INTO audit_logs (
            action, entity_type, entity_id, actor, details, created_at,
            actor_user_id, actor_username, target, timestamp, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            action,
            entity_type,
            entity_id,
            legacy_actor,
            details,
            timestamp,
            actor_user_id,
            actor_username,
            target,
            timestamp,
            status,
        ),
    )
    conn.commit()
    conn.close()


def get_or_create_attendance_session(
    class_id,
    deadline_hour=8,
    deadline_minute=0,
    session_name="Default",
):
    conn = get_connection()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute(
        """
        SELECT id FROM attendance_sessions
        WHERE class_id=? AND session_date=? AND session_name=?
        """,
        (class_id, today, session_name),
    )
    row = c.fetchone()
    if row:
        conn.close()
        return row[0]

    c.execute(
        """
        INSERT INTO attendance_sessions (
            class_id, session_date, session_name, start_time,
            deadline_hour, deadline_minute, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            class_id,
            today,
            session_name,
            datetime.now().isoformat(),
            deadline_hour,
            deadline_minute,
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    session_id = c.lastrowid
    conn.close()
    return session_id


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


def ensure_default_class(class_name=DEFAULT_CLASS_NAME):
    """Create the demo class if needed and return its id."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM classes WHERE class_name=?", (class_name,))
    row = c.fetchone()
    if row:
        conn.close()
        return row[0]

    c.execute(
        "INSERT INTO classes (class_name, created_at) VALUES (?, ?)",
        (class_name, datetime.now().isoformat()),
    )
    conn.commit()
    class_id = c.lastrowid
    conn.close()
    return class_id


def class_has_roster(class_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM class_students WHERE class_id=? LIMIT 1", (class_id,))
    has_roster = c.fetchone() is not None
    conn.close()
    return has_roster


def ensure_default_roster(class_id, existing_faces=None):
    """Populate a class with 30 demo students. Returns (added_count, skipped_count)."""
    if existing_faces is None:
        existing_faces = set()

    backup_sqlite_db(DB_PATH)
    conn = get_connection()
    c = conn.cursor()
    added = 0
    skipped = 0

    for mssv, full_name in DEFAULT_ROSTER:
        if not mssv or not full_name:
            skipped += 1
            continue

        assumed_db_key = full_name.replace(" ", "_")
        db_key_to_set = assumed_db_key if assumed_db_key in existing_faces else None

        c.execute("SELECT id, db_key FROM students WHERE mssv=?", (mssv,))
        row = c.fetchone()
        if row:
            student_id, current_db_key = row
            c.execute("UPDATE students SET full_name=? WHERE id=?", (full_name, student_id))
            if db_key_to_set and current_db_key != db_key_to_set:
                c.execute("UPDATE students SET db_key=? WHERE id=?", (db_key_to_set, student_id))
        else:
            c.execute(
                "INSERT INTO students (mssv, full_name, db_key) VALUES (?, ?, ?)",
                (mssv, full_name, db_key_to_set),
            )
            student_id = c.lastrowid

        c.execute(
            "INSERT OR IGNORE INTO class_students (class_id, student_id) VALUES (?, ?)",
            (class_id, student_id),
        )
        added += 1

    conn.commit()
    _sync_face_identities(conn)
    conn.close()
    write_audit_log(
        "roster.default_applied",
        entity_type="class",
        entity_id=str(class_id),
        details=f"added={added};skipped={skipped}",
    )
    return added, skipped


def _next_demo_mssv(cursor):
    cursor.execute("SELECT mssv FROM students WHERE mssv LIKE 'DEMO%'")
    used = {row[0] for row in cursor.fetchall()}
    idx = len(used) + 1
    while True:
        candidate = f"DEMO{idx:03d}"
        if candidate not in used:
            return candidate
        idx += 1


def ensure_student_in_class(class_id, full_name, db_key, mssv=None):
    """Create/link a demo student and attach it to the selected class."""
    full_name = str(full_name).strip()
    db_key = str(db_key).strip()
    if not full_name or not db_key:
        return None

    backup_sqlite_db(DB_PATH)
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT id, mssv FROM students WHERE db_key=?", (db_key,))
    row = c.fetchone()
    if row:
        student_id = row[0]
        c.execute("UPDATE students SET full_name=? WHERE id=?", (full_name, student_id))
    else:
        if not mssv:
            mssv = _next_demo_mssv(c)
        c.execute(
            """
            INSERT INTO students (mssv, full_name, db_key)
            VALUES (?, ?, ?)
            ON CONFLICT(mssv) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                db_key = EXCLUDED.db_key
            """,
            (mssv, full_name, db_key),
        )
        c.execute("SELECT id FROM students WHERE mssv=?", (mssv,))
        student_id = c.fetchone()[0]

    c.execute(
        "INSERT OR IGNORE INTO class_students (class_id, student_id) VALUES (?, ?)",
        (class_id, student_id),
    )
    conn.commit()
    _sync_face_identities(conn)
    conn.close()
    return student_id


def delete_class(class_id):
    backup_sqlite_db(DB_PATH)
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM class_students WHERE class_id=?", (class_id,))
    c.execute("DELETE FROM attendance WHERE class_id=?", (class_id,))
    c.execute("DELETE FROM classes WHERE id=?", (class_id,))
    conn.commit()
    conn.close()
    write_audit_log("class.deleted", entity_type="class", entity_id=str(class_id))


# --------------- Student / Roster ---------------

def upload_roster(class_id, df, existing_faces=None):
    """Import roster from DataFrame with columns 'MSSV' and 'FullName'.
    Returns (added_count, skipped_count).
    """
    valid, message = validate_roster_dataframe(df)
    if not valid:
        raise ValueError(message)

    if existing_faces is None:
        existing_faces = set()

    backup_sqlite_db(DB_PATH)
        
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
    _sync_face_identities(conn)
    conn.close()
    write_audit_log(
        "roster.imported",
        entity_type="class",
        entity_id=str(class_id),
        details=f"added={added};skipped={skipped}",
    )
    return added, skipped


def validate_roster_dataframe(df):
    required_id = "MSSV"
    name_options = {"FullName", "Họ và Tên"}
    columns = set(df.columns)
    if required_id not in columns:
        return False, "Roster thiếu cột MSSV."
    if not columns.intersection(name_options):
        return False, "Roster thiếu cột FullName hoặc Họ và Tên."
    if df.empty:
        return False, "Roster không có sinh viên."
    return True, "OK"


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


def get_class_db_keys(class_id):
    """Get linked face database keys for students in a class."""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        SELECT s.db_key
        FROM students s
        JOIN class_students cs ON s.id = cs.student_id
        WHERE cs.class_id = ?
          AND s.db_key IS NOT NULL
          AND TRIM(s.db_key) != ''
        """,
        (class_id,),
    )
    keys = {row[0] for row in c.fetchall()}
    conn.close()
    return keys


def get_all_students():
    """Get all students."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, mssv, full_name, db_key FROM students ORDER BY full_name", conn)
    conn.close()
    return df


def link_student_face(mssv, db_key):
    """Link a student MSSV to a face database key."""
    backup_sqlite_db(DB_PATH)
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE students SET db_key=? WHERE mssv=?", (db_key, mssv))
    conn.commit()
    _sync_face_identities(conn)
    conn.close()
    write_audit_log(
        "student.face_linked",
        entity_type="student",
        entity_id=mssv,
        details=f"db_key={db_key}",
    )


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

    session_id = get_or_create_attendance_session(
        class_id, deadline_hour, deadline_minute
    )

    c.execute("SELECT id FROM students WHERE db_key=?", (db_key,))
    student_row = c.fetchone()
    student_id = student_row[0] if student_row else None

    # Check if already attended today for this class. The legacy uniqueness
    # constraint is still date-based for backward compatibility.
    c.execute("SELECT id FROM attendance WHERE student_db_key=? AND class_id=? AND date=?",
              (db_key, class_id, today))
    if c.fetchone() is not None:
        conn.close()
        return False, None  # Already attended

    # Determine status based on deadline
    deadline = time(hour=deadline_hour, minute=deadline_minute).isoformat()
    current_time = now.time().isoformat()
    status = "PRESENT" if current_time <= deadline else "LATE"

    c.execute(
        """
        INSERT INTO attendance (
            student_db_key, class_id, date, timestamp, confidence,
            status, session_id, student_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            db_key,
            class_id,
            today,
            now.isoformat(),
            confidence,
            status,
            session_id,
            student_id,
        ),
    )
    conn.commit()
    conn.close()
    write_audit_log(
        "attendance.logged",
        entity_type="attendance",
        entity_id=db_key,
        details=f"class_id={class_id};session_id={session_id};confidence={confidence}",
    )
    return True, status


def record_recognition_event(
    class_id,
    student_db_key,
    decision,
    confidence,
    distance=None,
    gap=None,
    session_id=None,
    liveness_score=None,
    liveness_label=None,
    attack_type=None,
    liveness_reasons=None,
    recognition_score=None,
    live_score=None,
    print_score=None,
    replay_score=None,
    spoof_score=None,
    attendance_logged=0,
):
    if session_id is None and class_id is not None:
        session_id = get_or_create_attendance_session(class_id)
    if isinstance(liveness_reasons, (list, tuple)):
        liveness_reasons = json.dumps(list(liveness_reasons), ensure_ascii=True)
    if recognition_score is None:
        recognition_score = confidence
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO recognition_events (
            class_id, session_id, student_db_key, decision,
            confidence, distance, gap, created_at,
            liveness_score, liveness_label, attack_type,
            liveness_reasons, recognition_score,
            live_score, print_score, replay_score, spoof_score,
            attendance_logged
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            class_id,
            session_id,
            student_db_key,
            decision,
            confidence,
            distance,
            gap,
            datetime.now().isoformat(),
            liveness_score,
            liveness_label,
            attack_type,
            liveness_reasons,
            recognition_score,
            live_score,
            print_score,
            replay_score,
            spoof_score,
            attendance_logged,
        ),
    )
    conn.commit()
    conn.close()


def get_recognition_stats(class_id=None, limit=50):
    conn = get_connection()
    if class_id is None:
        query = """
            SELECT decision, COUNT(*) AS count, AVG(confidence) AS avg_confidence
            FROM recognition_events
            GROUP BY decision
            ORDER BY count DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(limit,))
    else:
        query = """
            SELECT decision, COUNT(*) AS count, AVG(confidence) AS avg_confidence
            FROM recognition_events
            WHERE class_id=?
            GROUP BY decision
            ORDER BY count DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(class_id, limit))
    conn.close()
    return df


def get_recent_audit_logs(limit=20):
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT
            COALESCE(timestamp, created_at) AS timestamp,
            created_at,
            action,
            target,
            entity_type,
            entity_id,
            actor_user_id,
            actor_username,
            actor,
            status,
            details
        FROM audit_logs
        ORDER BY id DESC
        LIMIT ?
        """,
        conn,
        params=(limit,),
    )
    conn.close()
    return df


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
    write_audit_log(
        "report.exported",
        entity_type="class" if class_id else "attendance",
        entity_id=str(class_id) if class_id else None,
        details=f"path={export_path};rows={len(df)}",
    )
    return export_path


def clear_attendance(class_id=None):
    backup_sqlite_db(DB_PATH)
    conn = get_connection()
    c = conn.cursor()
    if class_id:
        today = datetime.now().strftime("%Y-%m-%d")
        c.execute("DELETE FROM attendance WHERE class_id=? AND date=?", (class_id, today))
    else:
        c.execute("DELETE FROM attendance")
    conn.commit()
    conn.close()
    write_audit_log(
        "attendance.cleared",
        entity_type="class" if class_id else "attendance",
        entity_id=str(class_id) if class_id else None,
    )


init_db()
