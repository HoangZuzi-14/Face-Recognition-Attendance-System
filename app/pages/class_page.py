"""Class management page UI components."""

import streamlit as st
from services.class_service import ClassService
from app.auth import can_perform


def render_class_selector(class_service: ClassService, default_class_id):
    """Renders the dropdown selectbox to choose a class and updates st.session_state.selected_class_id."""
    classes_df = class_service.get_classes()
    if not classes_df.empty:
        class_options = {row["class_name"]: row["id"] for _, row in classes_df.iterrows()}
        
        # Determine current selection index
        current_selection = st.session_state.get("selected_class_id")
        if current_selection is None:
            current_selection = default_class_id
            
        index = 0
        if current_selection in class_options.values():
            index = list(class_options.values()).index(current_selection)
            
        selected_class_name = st.selectbox(
            "Chọn lớp",
            options=list(class_options.keys()),
            index=index,
            label_visibility="collapsed",
            key="class_select"
        )
        st.session_state.selected_class_id = class_options[selected_class_name]
    else:
        st.info("Chưa có lớp nào.")
        st.session_state.selected_class_id = None


def render_class_info(class_service: ClassService):
    """Renders the class information card under st.session_state.selected_class_id."""
    selected_class_id = st.session_state.get("selected_class_id")
    if selected_class_id:
        roster = class_service.get_class_roster(selected_class_id)
        st.session_state.roster_ready = not roster.empty
        count_reg = 0
        if not roster.empty:
            count_reg = len(roster[roster["db_key"].notna()])
            
        # Get selected class name
        classes_df = class_service.get_classes()
        class_name = "N/A"
        if not classes_df.empty:
            row = classes_df[classes_df["id"] == selected_class_id]
            if not row.empty:
                class_name = row.iloc[0]["class_name"]

        st.markdown(f'''
            <div class="mockup-info-row"><span class="mockup-info-label">Học phần</span><span class="mockup-info-value">{class_name}</span></div>
            <div class="mockup-info-row"><span class="mockup-info-label">Giảng viên</span><span class="mockup-info-value">TS. Nguyễn Văn A</span></div>
            <div class="mockup-info-row"><span class="mockup-info-label">Sĩ số</span><span class="mockup-info-value">{len(roster)} sinh viên</span></div>
            <div class="mockup-info-row"><span class="mockup-info-label">Đã đăng ký</span><span class="mockup-info-value">{count_reg}/{len(roster)}</span></div>
        ''', unsafe_allow_html=True)
    else:
        st.info("Chưa có lớp nào được chọn.")
        st.session_state.roster_ready = False


def render_setup_tab(class_service: ClassService, user_role):
    """Renders the setup tab containing class creation and deletion interface."""
    st.markdown('<div style="font-size:1.1rem; font-weight:700; color:var(--on-surface); margin-top:0.5rem; margin-bottom:0.75rem; font-family:\'Cormorant Garamond\', serif; font-size:1.4rem;">Tạo lớp mới</div>', unsafe_allow_html=True)
    new_class_name = st.text_input("Tên lớp", placeholder="VD: OOP_2024", key="new_class")
    if st.button("Tạo lớp", key="btn_create_class", use_container_width=True) and new_class_name.strip():
        class_id = class_service.create_class(new_class_name.strip())
        if class_id:
            st.success(f"Đã tạo '{new_class_name}'!")
            st.rerun()
        else:
            st.error("Lớp đã tồn tại!")
            
    st.markdown("<hr style='margin: 1.5rem 0; border-color: var(--outline-variant); opacity: 0.5;'>", unsafe_allow_html=True)
    
    st.markdown('<div style="font-size:1.1rem; font-weight:700; color:var(--on-surface); margin-bottom:0.75rem; font-family:\'Cormorant Garamond\', serif; font-size:1.4rem;">Quản lý lớp học hiện tại</div>', unsafe_allow_html=True)
    selected_class_id = st.session_state.get("selected_class_id")
    if selected_class_id:
        classes_df = class_service.get_classes()
        class_name = "N/A"
        if not classes_df.empty:
            row = classes_df[classes_df["id"] == selected_class_id]
            if not row.empty:
                class_name = row.iloc[0]["class_name"]
                
        st.warning(f"Thao tác sau sẽ xoá hoàn toàn lớp **{class_name}** cùng danh sách sinh viên và toàn bộ dữ liệu điểm danh liên quan!")
        
        delete_btn = st.button(
            "Xoá lớp hiện tại",
            key="btn_delete_class",
            use_container_width=True,
            disabled=not can_perform(user_role, "class.delete"),
        )
        
        if delete_btn:
            if can_perform(user_role, "class.delete"):
                class_service.delete_class(selected_class_id)
                st.session_state.selected_class_id = None
                st.success(f"Đã xoá lớp {class_name}!")
                st.rerun()
            else:
                st.warning("Vai trò hiện tại không có quyền xoá lớp.")
        if not can_perform(user_role, "class.delete"):
            st.caption("Vai trò hiện tại không có quyền xoá lớp.")
    else:
        st.caption("Hãy tạo hoặc chọn một lớp học.")
