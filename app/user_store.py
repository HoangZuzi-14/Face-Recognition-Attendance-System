"""Database-backed user lookup and authentication helpers."""

from app.auth import sanitize_user_for_session, verify_password
from app.database import get_connection


def _row_to_user(row):
    if row is None:
        return None
    return {
        "id": row[0],
        "username": row[1],
        "password_hash": row[2],
        "role": row[3],
        "is_active": row[4],
    }


def get_user_by_username(username, include_hash=False):
    username = str(username or "").strip()
    if not username:
        return None

    conn = get_connection()
    row = conn.execute(
        """
        SELECT id, username, password_hash, role, is_active
        FROM users
        WHERE username=?
        """,
        (username,),
    ).fetchone()
    conn.close()

    user = _row_to_user(row)
    if user is None:
        return None
    if include_hash:
        return user
    return sanitize_user_for_session(user)


def authenticate_user(username, password):
    user = get_user_by_username(username, include_hash=True)
    if user is None or int(user["is_active"]) != 1:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return sanitize_user_for_session(user)
