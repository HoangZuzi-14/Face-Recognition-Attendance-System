"""Streamlit login/session UI."""

import streamlit as st

from app.audit_context import clear_current_user, set_current_user
from app.auth import (
    SESSION_USER_KEY,
    clear_session_user,
    get_session_user,
    set_session_user,
)
from app.user_store import authenticate_user


def render_login_gate():
    """Require a valid login before the main Streamlit app renders."""
    current_user = get_session_user(st.session_state)
    if current_user:
        st.session_state["user_role"] = current_user["role"]
        set_current_user(current_user)
        return current_user

    clear_current_user()
    st.markdown(
        '<h1 class="page-title" style="margin-top:-1rem;">Dang nhap he thong</h1>',
        unsafe_allow_html=True,
    )
    
    # Quick login buttons
    import os
    admin_user = os.environ.get("ATTENDANCE_ADMIN_USERNAME", "admin").strip() or "admin"
    admin_pass = os.environ.get("ATTENDANCE_ADMIN_PASSWORD", "admin123").strip() or "admin123"
    teacher_user = os.environ.get("ATTENDANCE_TEACHER_USERNAME", "teacher").strip() or "teacher"
    teacher_pass = os.environ.get("ATTENDANCE_TEACHER_PASSWORD", "teacher123").strip() or "teacher123"

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔑 Đăng nhập nhanh Admin", use_container_width=True):
            user = authenticate_user(admin_user, admin_pass)
            if user:
                set_session_user(st.session_state, user)
                set_current_user(user)
                st.rerun()
    with col2:
        if st.button("👨‍🏫 Đăng nhập nhanh Teacher", use_container_width=True):
            user = authenticate_user(teacher_user, teacher_pass)
            if user:
                set_session_user(st.session_state, user)
                set_current_user(user)
                st.rerun()

    st.markdown("<div style='margin-top: 1.5rem;'>Hoặc đăng nhập thủ công:</div>", unsafe_allow_html=True)
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Tai khoan", key="login_username")
        password = st.text_input("Mat khau", type="password", key="login_password")
        submitted = st.form_submit_button("Dang nhap", use_container_width=True)

    if submitted:
        user = authenticate_user(username, password)
        if user:
            set_session_user(st.session_state, user)
            set_current_user(user)
            st.rerun()
        st.error("Tai khoan hoac mat khau khong dung, hoac user da bi khoa.")

    st.info(
        "Tai khoan mac dinh: admin / admin123 va teacher / teacher123 "
        "neu chua cau hinh bien moi truong."
    )
    st.stop()


def render_logout_control():
    current_user = st.session_state.get(SESSION_USER_KEY)
    if not current_user:
        return
    st.caption(f"{current_user['username']} ({current_user['role']})")
    if st.button("Dang xuat", key="btn_logout", use_container_width=True):
        clear_session_user(st.session_state)
        clear_current_user()
        st.rerun()
