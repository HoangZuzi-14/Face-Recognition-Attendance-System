"""Per-request audit actor context."""

from contextvars import ContextVar

from app.auth import sanitize_user_for_session

_CURRENT_USER = ContextVar("current_audit_user", default=None)


def set_current_user(user):
    """Set the current user for audit writes in this execution context."""
    return _CURRENT_USER.set(sanitize_user_for_session(user))


def clear_current_user():
    _CURRENT_USER.set(None)


def get_current_user():
    return _CURRENT_USER.get()


def get_current_actor():
    user = get_current_user()
    if not user:
        return None, "system"
    return user["id"], user["username"]
