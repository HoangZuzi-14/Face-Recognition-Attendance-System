"""Service for audit logging operations."""

from repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, repo=None):
        self._repo = repo or AuditRepository()

    def log(
        self,
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
        self._repo.log(
            action,
            entity_type,
            entity_id,
            actor,
            details,
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            target=target,
            status=status,
        )

    def get_recent_logs(self, limit=20):
        return self._repo.get_recent_logs(limit)
