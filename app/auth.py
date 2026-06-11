ROLE_ADMIN = "admin"
ROLE_TEACHER = "teacher"
ROLE_VIEWER = "viewer"
SESSION_USER_KEY = "current_user"

try:
    import bcrypt
except ImportError:  # pragma: no cover - exercised only in misconfigured envs
    bcrypt = None

PERMISSIONS = {
    ROLE_ADMIN: {
        "attendance.run",
        "attendance.clear",
        "class.delete",
        "roster.import",
        "face.register",
        "report.export",
        "system.monitor",
    },
    ROLE_TEACHER: {
        "attendance.run",
        "face.register",
        "report.export",
        "system.monitor",
    },
    ROLE_VIEWER: {
        "system.monitor",
    },
}


def can_perform(role, permission):
    return permission in PERMISSIONS.get(role, set())


def _require_bcrypt():
    if bcrypt is None:
        raise RuntimeError(
            "bcrypt is required for password hashing. Install requirements.txt first."
        )


def hash_password(password):
    """Hash a plaintext password with bcrypt."""
    if not isinstance(password, str) or not password:
        raise ValueError("password must be a non-empty string")
    _require_bcrypt()
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, password_hash):
    """Return True when a plaintext password matches a bcrypt hash."""
    if not password or not password_hash:
        return False
    _require_bcrypt()
    try:
        return bcrypt.checkpw(
            str(password).encode("utf-8"),
            str(password_hash).encode("utf-8"),
        )
    except (TypeError, ValueError):
        return False


def sanitize_user_for_session(user):
    """Keep only non-sensitive user fields in Streamlit session state."""
    if not user:
        return None
    return {
        "id": int(user["id"]),
        "username": str(user["username"]),
        "role": str(user["role"]),
    }


def set_session_user(session_state, user):
    session_user = sanitize_user_for_session(user)
    session_state[SESSION_USER_KEY] = session_user
    session_state["user_role"] = session_user["role"]
    return session_user


def get_session_user(session_state):
    return sanitize_user_for_session(session_state.get(SESSION_USER_KEY))


def clear_session_user(session_state):
    session_state.pop(SESSION_USER_KEY, None)
    session_state.pop("user_role", None)


def is_admin(user):
    return bool(user) and user.get("role") == ROLE_ADMIN
