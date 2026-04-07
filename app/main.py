import streamlit as st
import cv2
import sys
import os
import time
import pandas as pd
from datetime import datetime
import textwrap

# Ensure the root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.ui_components import (
    inject_custom_css, render_navbar, render_tabs, 
    render_footer, render_attendance_html
)
from app.database import (
    get_classes, create_class, delete_class,
    upload_roster, get_class_roster,
    get_full_attendance, export_csv, clear_attendance,
    link_student_face, get_all_students
)
from app.add_face import (
    save_captured_frame, preprocess_person,
    extract_and_merge_embedding, get_existing_count,
    clear_person_data
)
from src.recognize import process_frame, load_db, reload_db, reset_trackers

# ──────────────────────────────────────────────
# Page config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="ZuzoNKT – Điểm Danh Thông Minh",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ──────────────────────────────────────────────
# Custom CSS – matching Stitch design
# ──────────────────────────────────────────────
# Custom Fonts & Icons
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet" />
""", unsafe_allow_html=True)
inject_custom_css()

# ──────────────────────────────────────────────
# Top Navbar
# ──────────────────────────────────────────────
render_navbar()

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
if "db" not in st.session_state:
    st.session_state.db = load_db()
if "capture_mode" not in st.session_state:
    st.session_state.capture_mode = False
if "captured_count" not in st.session_state:
    st.session_state.captured_count = 0
if "capture_person_key" not in st.session_state:
    st.session_state.capture_person_key = None

# ──────────────────────────────────────────────
# Title + Tabs
# ──────────────────────────────────────────────
st.markdown('<h1 class="page-title" style="margin-top:-1rem;">Hệ Thống Điểm Danh Thông Minh</h1>', unsafe_allow_html=True)
render_tabs()

# ──────────────────────────────────────────────
# 50-50 Dashboard Layout
# ──────────────────────────────────────────────
db = st.session_state.db

col_left, col_right = st.columns(2, gap="large")

# ═══════════════════════════════════════════════
# LEFT COLUMN: Webcam + Controls
# ═══════════════════════════════════════════════
with col_left:
    # ── Camera UI ──    
    # Camera Container
    FRAME_WINDOW = st.image([], use_column_width=True)
    
    # Cam Action Buttons Row
    st.markdown('<div class="cam-btns-row">', unsafe_allow_html=True)
    if st.button("Bật/Tắt Camera", key="btn_toggle_cam", use_container_width=True):
        st.session_state.run = not st.session_state.run
        st.rerun()
    # Capture Mode Instructions Overlay
    if st.session_state.capture_mode and st.session_state.run:
        st.markdown(f'''
            <div class="focus-warning" style="margin-top: 1rem;">
                <b>Lưu ý:</b> Trình duyệt chặn phím SPACE. <br/>
                Hãy click vào cửa sổ <b>"Capture Face"</b> dưới taskbar rồi nhấn <b>SPACE</b> để chụp.
            </div>
        ''', unsafe_allow_html=True)
        if st.button("Hoàn tất & Lưu", key="btn_finish_cap", use_container_width=True):
            st.session_state.capture_mode = False
            if st.session_state.captured_count > 0:
                with st.spinner("Đang trích xuất dữ liệu..."):
                    valid = preprocess_person(st.session_state.capture_person_key)
                    if valid > 0:
                        extract_and_merge_embedding(st.session_state.capture_person_key)
                        st.session_state.db = reload_db()
                        reset_trackers()
                        st.success("Thành công!")
            st.session_state.captured_count = 0
            st.session_state.capture_person_key = None
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Class Information Card ──
    st.markdown('<div style="text-transform:uppercase; font-size:0.75rem; font-weight:700; color:#5b403c; margin-bottom:1.5rem; letter-spacing:0.05em;">Thông Tin Lớp Học</div>', unsafe_allow_html=True)
    
    classes_df = get_classes()
    if not classes_df.empty:
        class_options = {row["class_name"]: row["id"] for _, row in classes_df.iterrows()}
        selected_class_name = st.selectbox(
            "Chọn lớp",
            options=list(class_options.keys()),
            index=0, label_visibility="collapsed",
            key="class_select"
        )
        st.session_state.selected_class_id = class_options[selected_class_name]
    else:
        st.info("Chưa có lớp nào.")
        st.session_state.selected_class_id = None

    if st.session_state.selected_class_id:
        roster = get_class_roster(st.session_state.selected_class_id)
        students = get_all_students()
        count_reg = 0
        # Simplified logic for mockup display
        if not roster.empty:
            count_reg = len(roster[roster["db_key"].notna()])
            
        st.markdown(f'''
            <div class="mockup-info-row"><span class="mockup-info-label">Học phần</span><span class="mockup-info-value">{selected_class_name}</span></div>
            <div class="mockup-info-row"><span class="mockup-info-label">Giảng viên</span><span class="mockup-info-value">TS. Nguyễn Văn A</span></div>
            <div class="mockup-info-row"><span class="mockup-info-label">Sĩ số</span><span class="mockup-info-value">{len(roster)} sinh viên</span></div>
            <div class="mockup-info-row"><span class="mockup-info-label">Đã đăng ký</span><span class="mockup-info-value">{count_reg}/{len(roster)}</span></div>
        ''', unsafe_allow_html=True)
    else:
        st.info("Chưa có lớp nào được chọn.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Deadline config
    from datetime import time as dt_time
    deadline_val = st.time_input(
        "Deadline điểm danh",
        value=dt_time(st.session_state.deadline_hour, st.session_state.deadline_minute),
        key="deadline_time"
    )
    
    st.session_state.deadline_hour = deadline_val.hour
    st.session_state.deadline_minute = deadline_val.minute

    # ── Action panels ──
    with st.expander("Tạo lớp mới"):
            new_class_name = st.text_input("Tên lớp", placeholder="VD: OOP_2024", key="new_class")
            if st.button("Tạo", key="btn_create_class", use_container_width=True) and new_class_name.strip():
                class_id = create_class(new_class_name.strip())
                if class_id:
                    st.success(f"Đã tạo '{new_class_name}'!")
                    st.rerun()
                else:
                    st.error("Lớp đã tồn tại!")

    @st.cache_data
    def get_sample_csv():
        sample_data = {
            "MSSV": [
                "20230001", "20220002", "20210003", "202400004", "202500005",
                "20230006", "20220007", "20210008", "202400009", "202500010"
            ],
            "FullName": [
                "George W Bush", "Colin Powell", "Tony Blair", "Donald Rumsfeld", "Gerhard Schroeder",
                "Ariel Sharon", "Hugo Chavez", "Junichiro Koizumi", "Jean Chretien", "John Ashcroft"
            ]
        }
        df = pd.DataFrame(sample_data)
        return df.to_csv(index=False).encode('utf-8')

    with st.expander("Upload danh sách"):
            if st.session_state.selected_class_id is not None:
                st.download_button(
                    label="Tải file CSV mẫu",
                    data=get_sample_csv(),
                    file_name="danh_sach_mau.csv",
                    mime="text/csv",
                    use_container_width=True
                )
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
                        required_cols = {"MSSV", "FullName"}
                        fallback_cols = {"MSSV", "Họ và Tên"}
                        
                        if not required_cols.issubset(set(roster_df.columns)) and not fallback_cols.issubset(set(roster_df.columns)):
                            st.error(f"Cần có cột: {required_cols}")
                        else:
                            st.dataframe(roster_df.head(3), use_container_width=True, hide_index=True)
                            if st.button("Import", key="btn_import", use_container_width=True):
                                existing_faces = set(st.session_state.db.keys()) if st.session_state.db else set()
                                added, skipped = upload_roster(
                                    st.session_state.selected_class_id, roster_df, existing_faces
                                )
                                st.success(f"+{added} SV, bỏ qua {skipped}")
                                st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
            else:
                st.caption("Tạo lớp trước.")

    with st.expander("Thêm người mới/Cập nhật thêm ảnh"):
            if not st.session_state.capture_mode:
                add_mode = st.radio(
                    "Cách thêm", ["Từ UNKNOWN", "Nhập tên mới/cũ"],
                    horizontal=True, key="add_mode", label_visibility="collapsed"
                )
                if add_mode == "Từ UNKNOWN":
                    students_df = get_all_students()
                    unknown_students = students_df[students_df["db_key"].isna()]
                    if not unknown_students.empty:
                        options = {
                            f"{row['mssv']} - {row['full_name']}": row
                            for _, row in unknown_students.iterrows()
                        }
                        selected = st.selectbox("Chọn SV", list(options.keys()), key="unknown_sv")
                        student_row = options[selected]
                        suggested_key = student_row["full_name"].replace(" ", "_")
                        db_key = st.text_input("DB key", value=suggested_key, key="db_key_input")
                        if st.button("Bắt đầu chụp", key="btn_capture_unknown", use_container_width=True):
                            if db_key.strip():
                                link_student_face(student_row["mssv"], db_key.strip())
                                st.session_state.capture_mode = True
                                st.session_state.capture_person_key = db_key.strip()
                                st.session_state.captured_count = get_existing_count(db_key.strip())
                                st.rerun()
                    else:
                        st.caption("Không có SV UNKNOWN.")
                else:
                    new_key = st.text_input("Tên (dùng _)", placeholder="VD: Nguyen_Van_A", key="new_key")
                    if st.button("Bắt đầu chụp", key="btn_capture_new", use_container_width=True):
                        if new_key.strip():
                            st.session_state.capture_mode = True
                            st.session_state.capture_person_key = new_key.strip()
                            st.session_state.captured_count = get_existing_count(new_key.strip())
                            st.rerun()
            else:
                st.warning(f"Đang chụp: {st.session_state.capture_person_key}")
                st.caption(f"Đã chụp: {st.session_state.captured_count} ảnh")
                if st.button("Huỷ", key="btn_cancel_capture", use_container_width=True):
                    clear_person_data(st.session_state.capture_person_key)
                    st.session_state.capture_mode = False
                    st.session_state.captured_count = 0
                    st.session_state.capture_person_key = None
                    st.rerun()


# ═══════════════════════════════════════════════
# RIGHT COLUMN: Attendance Table
# ═══════════════════════════════════════════════
with col_right:

    if st.session_state.selected_class_id is not None:
        # Header
        st.markdown(f'<div style="font-size:1.5rem; font-weight:800; color:#1b1c1c; margin-bottom:0.25rem;">Danh Sách Điểm Danh</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="color:#5b403c; font-size:0.8rem; margin-bottom:1.5rem;">Cập nhật lúc: {datetime.now().strftime("%H:%M SA, %d/%m/%Y")}</div>', unsafe_allow_html=True)

        # Action buttons
        btn_row1, btn_row2, btn_row3 = st.columns(3)
        with btn_row1:
            export_btn = st.button("Export CSV", key="btn_export", use_container_width=True)
        with btn_row2:
            clear_btn = st.button("Xoá bảng", key="btn_clear", use_container_width=True)
        with btn_row3:
            if not classes_df.empty and st.session_state.selected_class_id:
                delete_btn = st.button("Xoá lớp", key="btn_delete_class", use_container_width=True)
            else:
                delete_btn = False

        if clear_btn:
            clear_attendance(st.session_state.selected_class_id)
            reset_trackers()
            st.rerun()

        if export_btn:
            csv_path = export_csv(st.session_state.selected_class_id)
            st.success(f"Exported to {csv_path}")

        if delete_btn:
            delete_class(st.session_state.selected_class_id)
            st.session_state.selected_class_id = None
            st.rerun()

        # Attendance table
        log_placeholder = st.empty()
        att_df = get_full_attendance(
            st.session_state.selected_class_id,
            st.session_state.deadline_hour,
            st.session_state.deadline_minute
        )

        # Uses render_attendance_html from ui_components

        log_placeholder.markdown(render_attendance_html(att_df), unsafe_allow_html=True)

        # Summary bar
        if not att_df.empty:
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
        log_placeholder = st.empty()


# ──────────────────────────────────────────────
# Footer
# ──────────────────────────────────────────────
render_footer()


# ──────────────────────────────────────────────
# Webcam Loop (runs at the bottom)
# ──────────────────────────────────────────────
run = st.session_state.run # Use the state from the button

if db is None:
    st.error("Dữ liệu Face DB trống!")
    st.stop()

cap = None
if run:
    cap = cv2.VideoCapture(st.session_state.cam_source)

if st.session_state.capture_mode and run and cap is not None and cap.isOpened():
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    person_key = st.session_state.capture_person_key

    while run and cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30, 30))

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        count = st.session_state.captured_count
        cv2.putText(frame, f"Captured: {count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, f"Person: {person_key}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        cv2.putText(frame, "SPACE=capture  Q=finish", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)

        cv2.imshow("Capture Face", frame)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        FRAME_WINDOW.image(frame_rgb)

        key = cv2.waitKey(1)
        if key == ord(' ') and len(faces) > 0:
            idx = st.session_state.captured_count
            save_captured_frame(person_key, frame, idx)
            st.session_state.captured_count += 1
        elif key == ord('q'):
            break

        time.sleep(0.03)

    cap.release()
    cv2.destroyAllWindows()

elif run and cap is not None and cap.isOpened():
    while run and cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        processed_frame = process_frame(
            frame, db,
            class_id=st.session_state.selected_class_id,
            deadline_hour=st.session_state.deadline_hour,
            deadline_minute=st.session_state.deadline_minute
        )

        frame_rgb = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
        FRAME_WINDOW.image(frame_rgb)

        if st.session_state.selected_class_id is not None:
            att_df = get_full_attendance(
                st.session_state.selected_class_id,
                st.session_state.deadline_hour
            )
            log_placeholder.markdown(render_attendance_html(att_df), unsafe_allow_html=True)

        time.sleep(0.1)

if cap is not None:
    cap.release()
