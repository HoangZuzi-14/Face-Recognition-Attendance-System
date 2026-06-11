"""Repository for audit log database operations."""

import pandas as pd
from datetime import datetime

from app.database import get_connection, write_audit_log


class AuditRepository:
    """Handles audit log write and query operations."""

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
        """Write an audit log entry."""
        write_audit_log(
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
        """Get recent audit log entries."""
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
