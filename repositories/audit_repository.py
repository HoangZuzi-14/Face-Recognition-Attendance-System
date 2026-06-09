"""Repository for audit log database operations."""

import pandas as pd
from datetime import datetime

from app.database import get_connection, write_audit_log


class AuditRepository:
    """Handles audit log write and query operations."""

    def log(self, action, entity_type=None, entity_id=None, actor="system", details=None):
        """Write an audit log entry."""
        write_audit_log(action, entity_type, entity_id, actor, details)

    def get_recent_logs(self, limit=20):
        """Get recent audit log entries."""
        conn = get_connection()
        df = pd.read_sql_query(
            """
            SELECT created_at, action, entity_type, entity_id, actor, details
            FROM audit_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            conn,
            params=(limit,),
        )
        conn.close()
        return df
