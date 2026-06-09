"""System monitoring and logs page UI components."""

import streamlit as st
from services.recognition_service import RecognitionService
from services.audit_service import AuditService
from app.integrity import validate_integrity


def render_monitor_expander(recognition_service: RecognitionService, audit_service: AuditService):
    """Renders system metrics, audit logs, and data integrity verification tools."""
    selected_class_id = st.session_state.get("selected_class_id")
    
    with st.expander("Giám sát hệ thống"):
        monitor_tab, audit_tab, integrity_tab = st.tabs(
            ["Recognition", "Audit", "Integrity"]
        )
        
        with monitor_tab:
            stats_df = recognition_service.get_stats(selected_class_id)
            if stats_df.empty:
                st.caption("Chưa có recognition event.")
            else:
                st.dataframe(stats_df, use_container_width=True, hide_index=True)
                
        with audit_tab:
            audit_df = audit_service.get_recent_logs()
            if audit_df.empty:
                st.caption("Chưa có audit log.")
            else:
                st.dataframe(audit_df, use_container_width=True, hide_index=True)
                
        with integrity_tab:
            if st.button("Chạy kiểm tra integrity", key="btn_integrity", use_container_width=True):
                report = validate_integrity()
                if report.ok:
                    st.success("Integrity OK.")
                else:
                    st.warning("Phát hiện lệch dữ liệu.")
                st.text("\n".join(report.to_lines(max_items=8)))
