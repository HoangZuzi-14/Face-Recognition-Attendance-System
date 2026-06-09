"""Roster upload and management page UI components."""

import streamlit as st
import pandas as pd
from services.student_service import StudentService
from app.auth import can_perform
from app.database import DEFAULT_ROSTER


@st.cache_data
def get_sample_csv():
    """Generates sample CSV data from default roster."""
    sample_data = {
        "MSSV": [mssv for mssv, _ in DEFAULT_ROSTER],
        "FullName": [full_name for _, full_name in DEFAULT_ROSTER],
    }
    df = pd.DataFrame(sample_data)
    return df.to_csv(index=False).encode('utf-8')


def render_roster_tab(student_service: StudentService, user_role, db_keys):
    """Renders the Roster tab to set up class students."""
    selected_class_id = st.session_state.get("selected_class_id")
    if selected_class_id is not None:
        st.caption("Trước khi mở camera điểm danh, hãy dùng danh sách default hoặc upload roster.")
        
        # Use default roster button
        if st.button("Dùng danh sách default 30 sinh viên", key="btn_default_roster", use_container_width=True):
            if not can_perform(user_role, "roster.import"):
                st.warning("Vai trò hiện tại không có quyền cập nhật roster.")
                return
                
            existing_faces = set(db_keys) if db_keys else set()
            added, skipped = student_service.ensure_default_roster(
                selected_class_id, existing_faces
            )
            st.success(f"Đã sẵn sàng danh sách default: {added} SV, bỏ qua {skipped}")
            st.rerun()
            
        # Download sample template
        st.download_button(
            label="Tải file CSV mẫu",
            data=get_sample_csv(),
            file_name="danh_sach_mau.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # Roster file uploader
        uploaded_file = st.file_uploader(
            "CSV hoặc XLSX", type=["csv", "xlsx"],
            key="roster_uploader", label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    roster_df = pd.read_csv(uploaded_file, dtype=str)
                else:
                    roster_df = pd.read_excel(uploaded_file, dtype=str)
                    
                roster_valid, roster_message = student_service.validate_roster_dataframe(roster_df)
                
                if not roster_valid:
                    st.error(roster_message)
                else:
                    st.dataframe(roster_df.head(3), use_container_width=True, hide_index=True)
                    if st.button("Import", key="btn_import", use_container_width=True):
                        if not can_perform(user_role, "roster.import"):
                            st.warning("Vai trò hiện tại không có quyền import roster.")
                            return
                            
                        existing_faces = set(db_keys) if db_keys else set()
                        added, skipped = student_service.upload_roster(
                            selected_class_id, roster_df, existing_faces
                        )
                        st.success(f"+{added} SV, bỏ qua {skipped}")
                        st.rerun()
            except Exception as e:
                st.error(f"Lỗi: {e}")
    else:
        st.caption("Tạo hoặc chọn lớp trước.")
