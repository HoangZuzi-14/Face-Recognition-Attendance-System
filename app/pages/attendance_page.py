"""Attendance tracking and reporting page UI components."""

import streamlit as st
from datetime import datetime
from services.attendance_service import AttendanceService
from app.auth import can_perform
from src.recognize import reset_trackers


def render_attendance_header(attendance_service: AttendanceService, user_role) -> bool:
    """Renders attendance table action buttons. Returns True if any action triggered rerun."""
    selected_class_id = st.session_state.get("selected_class_id")
    if selected_class_id is None:
        return False

    st.markdown(f'<div style="font-size:1.5rem; font-weight:800; color:#1b1c1c; margin-bottom:0.25rem;">Danh Sách Điểm Danh</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="color:#5b403c; font-size:0.8rem; margin-bottom:1.5rem;">Cập nhật lúc: {datetime.now().strftime("%H:%M SA, %d/%m/%Y")}</div>', unsafe_allow_html=True)

    btn_row1, btn_row2 = st.columns(2)
    with btn_row1:
        export_btn = st.button(
            "Export CSV",
            key="btn_export",
            use_container_width=True,
            disabled=not can_perform(user_role, "report.export"),
        )
    with btn_row2:
        clear_btn = st.button(
            "Xoá bảng",
            key="btn_clear",
            use_container_width=True,
            disabled=not can_perform(user_role, "attendance.clear"),
        )

    if clear_btn:
        if can_perform(user_role, "attendance.clear"):
            attendance_service.clear_today(selected_class_id)
            reset_trackers()
            st.rerun()
            return True
        else:
            st.warning("Vai trò hiện tại không có quyền xoá bảng điểm danh.")

    if export_btn:
        if can_perform(user_role, "report.export"):
            csv_path = attendance_service.export_csv(selected_class_id)
            st.success(f"Exported to {csv_path}")
        else:
            st.warning("Vai trò hiện tại không có quyền export.")
            
    return False


def render_attendance_table(attendance_service: AttendanceService, deadline_hour, deadline_minute):
    """Fetches and displays the styled attendance table."""
    selected_class_id = st.session_state.get("selected_class_id")
    if selected_class_id is not None:
        att_df = attendance_service.get_full_attendance(
            selected_class_id,
            deadline_hour,
            deadline_minute
        )
        return att_df
    return None


def render_summary_bar(att_df):
    """Displays the present/late/absent summary statistics bar."""
    if att_df is not None and not att_df.empty:
        total = len(att_df)
        present = len(att_df[att_df["Trạng Thái"] == "PRESENT"])
        late = len(att_df[att_df["Trạng Thái"] == "LATE"])
        absent = len(att_df[att_df["Trạng Thái"] == "ABSENT"])
        unknown = len(att_df[att_df["Trạng Thái"] == "UNKNOWN"])

        st.markdown(f"""
        <div class="summary-bar">
            <span class="summary-chip"><span class="dot dot-present"></span>Present: {present}</span>
            <span class="summary-chip"><span class="dot dot-late"></span>Late: {late}</span>
            <span class="summary-chip"><span class="dot dot-absent"></span>Absent: {absent}</span>
            <span class="summary-chip"><span class="dot dot-unknown"></span>Unknown: {unknown}</span>
            <span class="summary-chip" style="margin-left:auto;font-weight:700;">Tổng: {total}</span>
        </div>
        """, unsafe_allow_html=True)
