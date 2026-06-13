import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
while ROOT_DIR in sys.path:
    sys.path.remove(ROOT_DIR)
sys.path.insert(0, ROOT_DIR)

import streamlit as st

from app.path_setup import ensure_repo_root_first

ensure_repo_root_first(__file__)

# UI Components
from app.ui_components import (
    inject_custom_css, render_navbar, render_tabs, 
    render_footer
)

# Services
from services.class_service import ClassService
from services.student_service import StudentService
from services.attendance_service import AttendanceService
from services.recognition_service import RecognitionService
from services.audit_service import AuditService

# Authentication & Access Control
from app.auth import can_perform
from app.auth_ui import render_login_gate, render_logout_control
from app.portal import portal_for_role

# Subpages UI
from app.pages.class_page import (
    render_class_selector, render_class_info, 
    render_setup_tab
)
from app.pages.roster_page import render_roster_tab
from app.pages.face_register_page import render_face_registration_tab, render_capture_ui
from app.pages.attendance_page import (
    render_attendance_header, render_attendance_table,
    render_summary_bar
)
from app.pages.monitor_page import render_monitor_expander
from app.config import NATIVE_DASHBOARD_REFRESH_SECONDS
from app.camera_profiles import DEFAULT_CAMERA_PROFILE
from app.native_camera import (
    get_native_camera_preflight,
    start_native_camera_session,
    stop_native_camera_session,
    sync_native_camera_state,
)

# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="ZuzoNKT – Điểm Danh Thông Minh",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Fonts & Icons
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet" />
""", unsafe_allow_html=True)
inject_custom_css()

# Render Navbar
render_navbar()

current_user = render_login_gate()

# Initialize Services
class_service = ClassService()
student_service = StudentService()
attendance_service = AttendanceService()
recognition_service = RecognitionService()
audit_service = AuditService()

# ──────────────────────────────────────────────
# Session state defaults
# ──────────────────────────────────────────────
if "deadline_hour" not in st.session_state:
    st.session_state.deadline_hour = 8
if "deadline_minute" not in st.session_state:
    st.session_state.deadline_minute = 0
if "selected_class_id" not in st.session_state:
    st.session_state.selected_class_id = None
if "cam_source" not in st.session_state:
    st.session_state.cam_source = 0
if "run" not in st.session_state:
    st.session_state.run = False
if "native_camera_process" not in st.session_state:
    st.session_state.native_camera_process = None
if "native_capture_process" not in st.session_state:
    st.session_state.native_capture_process = None
if "native_capture_person_key" not in st.session_state:
    st.session_state.native_capture_person_key = None
if "native_capture_should_open" not in st.session_state:
    st.session_state.native_capture_should_open = False
if "db" not in st.session_state:
    from src.recognize import load_db
    st.session_state.db = load_db()
if "capture_mode" not in st.session_state:
    st.session_state.capture_mode = False
if "captured_count" not in st.session_state:
    st.session_state.captured_count = 0
if "capture_person_key" not in st.session_state:
    st.session_state.capture_person_key = None
if "capture_rejected_count" not in st.session_state:
    st.session_state.capture_rejected_count = 0
if "capture_start_count" not in st.session_state:
    st.session_state.capture_start_count = 0
if "last_quality_message" not in st.session_state:
    st.session_state.last_quality_message = ""
if "roster_ready" not in st.session_state:
    st.session_state.roster_ready = False
st.session_state.user_role = current_user["role"]
current_portal = portal_for_role(st.session_state.user_role)

default_class_id = class_service.ensure_default_class()
if st.session_state.selected_class_id is None:
    st.session_state.selected_class_id = default_class_id
sync_native_camera_state(st.session_state)

# Title & Styled Navigation Tabs Header
st.markdown('<h1 class="page-title" style="margin-top:-1rem;">Hệ Thống Điểm Danh Thông Minh</h1>', unsafe_allow_html=True)
st.caption(f"{current_portal['label']} - {current_portal['description']}")
render_tabs()

db = st.session_state.db

def get_console_state():
    if st.session_state.capture_mode:
        return "REGISTERING", "Đăng ký khuôn mặt", "console-registering"
    if st.session_state.run:
        return "LIVE", "Đang điểm danh", "console-live"
    return "READY", "Sẵn sàng", "console-ready"

def permission_note(permission):
    if can_perform(st.session_state.user_role, permission):
        return ""
    return "Vai trò hiện tại không có quyền thực hiện thao tác này."


def render_attendance_dashboard():
    selected_class_id = st.session_state.selected_class_id
    if selected_class_id is not None:
        render_attendance_header(attendance_service, st.session_state.user_role)

        log_placeholder = st.empty()
        att_df = render_attendance_table(
            attendance_service,
            st.session_state.deadline_hour,
            st.session_state.deadline_minute
        )

        if att_df is not None:
            from app.ui_components import render_attendance_html
            log_placeholder.markdown(render_attendance_html(att_df), unsafe_allow_html=True)
            render_summary_bar(att_df)

        show_diagnostics = st.checkbox(
            "Developer diagnostics",
            value=False,
            key="show_diagnostics",
        )
        if show_diagnostics:
            render_monitor_expander(recognition_service, audit_service)
    else:
        st.markdown("""
        <div class="zuzo-card" style="min-height:400px;display:flex;align-items:center;justify-content:center;">
            <div style="text-align:center;">
                <div style="font-size:3rem;opacity:0.2;margin-bottom:0.5rem;"></div>
                <p style="color:var(--on-surface-variant);font-weight:500;">
                    Chọn hoặc tạo lớp bên trái để bắt đầu điểm danh.
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)


@st.fragment(run_every=NATIVE_DASHBOARD_REFRESH_SECONDS)
def render_live_attendance_dashboard():
    was_running = st.session_state.get("run", False)
    running = sync_native_camera_state(st.session_state)
    if was_running and not running:
        st.rerun()
    render_attendance_dashboard()


console_code, console_label, console_class = get_console_state()

col_left, col_right = st.columns([1.45, 1], gap="large")

# ═══════════════════════════════════════════════
# LEFT COLUMN: Webcam + Controls
# ═══════════════════════════════════════════════
with col_left:
    st.markdown(f"""
    <section class="console-hero {console_class}">
        <div class="console-topline">
            <span class="anthropic-mark">✣</span>
            <span>Live Attendance Console</span>
            <span class="console-state">{console_code}</span>
        </div>
        <div class="console-title">{console_label}</div>
        <div class="console-copy">
            Camera chạy bằng cửa sổ OpenCV native; dashboard web chỉ điều khiển và cập nhật bảng điểm danh.
        </div>
    </section>
    """, unsafe_allow_html=True)

    control_col1, control_col2, control_col3 = st.columns([1.1, 0.8, 0.9])
    with control_col1:
        render_logout_control()
    with control_col2:
        st.session_state.cam_source = st.number_input(
            "Camera",
            min_value=0,
            max_value=5,
            value=int(st.session_state.cam_source),
            step=1,
            key="cam_source_input",
            disabled=st.session_state.run,
        )
    with control_col3:
        from datetime import time as dt_time
        deadline_val = st.time_input(
            "Deadline",
            value=dt_time(st.session_state.deadline_hour, st.session_state.deadline_minute),
            key="deadline_time"
        )
        st.session_state.deadline_hour = deadline_val.hour
        st.session_state.deadline_minute = deadline_val.minute

    # Stable camera slot. Avoid replacing a custom component iframe through
    # st.empty(); stale iframe messages are noisy in browser devtools.
    FRAME_WINDOW = st.container()
    
    can_start_attendance = (
        st.session_state.capture_mode or
        (
            st.session_state.selected_class_id is not None and
            class_service.class_has_roster(st.session_state.selected_class_id)
        )
    )
    if not st.session_state.run and st.session_state.selected_class_id is not None:
        preflight = get_native_camera_preflight(
            class_id=st.session_state.selected_class_id
        )
        st.session_state.native_camera_preflight = preflight
        liveness_label = "enabled" if preflight["liveness_enabled"] else "disabled"
        st.caption(
            "Native preflight: "
            f"{preflight['active_identity_count']} active identities; "
            f"db.pkl {preflight['face_db_status']}; "
            f"SQLite {preflight['sqlite_status']}; "
            f"liveness {liveness_label}."
        )
    native_error = st.session_state.get("native_camera_error")
    if native_error:
        st.error(native_error)
    start_disabled = (
        not can_perform(st.session_state.user_role, "attendance.run")
        or (st.session_state.capture_mode and not st.session_state.run)
        or (not st.session_state.run and not can_start_attendance)
    )
    start_label = "Dừng điểm danh" if st.session_state.run else "Bắt đầu điểm danh"
    if st.button(start_label, key="btn_toggle_cam", use_container_width=True, disabled=start_disabled):
        if not can_perform(st.session_state.user_role, "attendance.run"):
            st.warning("Vai trò hiện tại không có quyền mở camera điểm danh.")
        elif not st.session_state.run and not can_start_attendance:
            st.warning("Vui lòng chọn danh sách default hoặc upload roster trước khi điểm danh.")
        else:
            if st.session_state.run:
                stop_native_camera_session(st.session_state)
            else:
                from src.recognize import reset_trackers
                attendance_service.clear_today(st.session_state.selected_class_id)
                reset_trackers()
                start_native_camera_session(
                    st.session_state,
                    camera_index=int(st.session_state.cam_source),
                    class_id=st.session_state.selected_class_id,
                    deadline_hour=st.session_state.deadline_hour,
                    deadline_minute=st.session_state.deadline_minute,
                    profile=DEFAULT_CAMERA_PROFILE,
                )
        st.rerun()
        
    if start_disabled and not st.session_state.run:
        if st.session_state.capture_mode:
            reason = "Đang đăng ký khuôn mặt; hoàn tất hoặc huỷ trước khi mở điểm danh."
        else:
            reason = permission_note("attendance.run") or "Cần chọn lớp có roster trước khi điểm danh."
        st.caption(reason)

    # Face capture mode render
    if st.session_state.capture_mode:
        render_capture_ui(FRAME_WINDOW)
    elif st.session_state.run:
        FRAME_WINDOW.markdown(
            """
            <div class="zuzo-card" style="min-height:220px;display:flex;align-items:center;justify-content:center;">
                <div style="text-align:center;color:var(--on-surface-variant);font-weight:600;">
                    Camera native đang chạy trong cửa sổ OpenCV riêng.<br/>
                    Nhấn Q/ESC trong cửa sổ camera hoặc Dừng điểm danh trên web để tắt.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        command = st.session_state.get("native_camera_command")
        if command and st.session_state.get("show_diagnostics", False):
            st.caption(command)
    elif not st.session_state.run:
        FRAME_WINDOW.markdown(
            """
            <div class="zuzo-card" style="min-height:360px;display:flex;align-items:center;justify-content:center;">
                <div style="text-align:center;color:var(--on-surface-variant);font-weight:600;">
                    Nhấn Bắt đầu điểm danh để mở cửa sổ camera native.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    # Class Information section
    st.markdown('<div style="text-transform:uppercase; font-size:0.75rem; font-weight:700; color:#5b403c; margin-bottom:1.5rem; letter-spacing:0.05em;">Thông Tin Lớp Học</div>', unsafe_allow_html=True)
    render_class_selector(class_service, default_class_id)
    render_class_info(class_service)

    # Action panels (role-specific portal tabs)
    tab_handles = st.tabs(list(current_portal["tab_labels"]))
    for tab_key, tab_handle in zip(current_portal["tabs"], tab_handles):
        with tab_handle:
            if tab_key == "setup":
                render_setup_tab(class_service, st.session_state.user_role)
            elif tab_key == "roster":
                render_roster_tab(student_service, st.session_state.user_role, db.keys() if db else None)
            elif tab_key == "face":
                render_face_registration_tab(student_service, st.session_state.user_role, default_class_id)

# ═══════════════════════════════════════════════
# RIGHT COLUMN: Attendance Table & Monitoring
# ═══════════════════════════════════════════════
with col_right:
    if st.session_state.run:
        render_live_attendance_dashboard()
    else:
        render_attendance_dashboard()

# Render Footer
render_footer()
