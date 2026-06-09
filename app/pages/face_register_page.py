"""Face registration and quality checking UI components."""

import streamlit as st
from services.student_service import StudentService
from app.auth import can_perform
from app.add_face import (
    finalize_face_registration, get_existing_count, clear_person_data
)
from app.capture_policy import (
    MIN_CAPTURE_IMAGES, RECOMMENDED_CAPTURE_IMAGES,
    can_finalize_capture, capture_progress_text
)
from app.camera_profiles import DEFAULT_CAMERA_PROFILE
from app.native_camera import stop_native_camera_session
from app.native_capture import (
    start_native_capture_session,
    stop_native_capture_session,
    sync_native_capture_state,
)
from src.recognize import reload_db, reset_trackers


def _reset_capture_state():
    st.session_state.capture_mode = False
    st.session_state.captured_count = 0
    st.session_state.capture_rejected_count = 0
    st.session_state.capture_start_count = 0
    st.session_state.last_quality_message = ""
    st.session_state.capture_person_key = None
    st.session_state.native_capture_should_open = False


def _begin_capture(person_key):
    stop_native_camera_session(st.session_state)
    stop_native_capture_session(st.session_state)
    existing_count = get_existing_count(person_key)
    st.session_state.capture_mode = True
    st.session_state.capture_person_key = person_key
    st.session_state.captured_count = existing_count
    st.session_state.capture_start_count = st.session_state.captured_count
    st.session_state.capture_rejected_count = 0
    st.session_state.last_quality_message = ""
    st.session_state.native_capture_should_open = False
    start_native_capture_session(
        st.session_state,
        camera_index=int(st.session_state.get("cam_source", 0)),
        person_key=person_key,
        start_index=existing_count,
        profile=DEFAULT_CAMERA_PROFILE,
    )


def render_capture_ui(frame_placeholder):
    """Renders the high-quality webcam capture UI for face registration."""
    if not st.session_state.get("capture_mode"):
        return

    person_key = st.session_state.capture_person_key
    current_count = get_existing_count(person_key)
    st.session_state.captured_count = current_count
    valid_count = current_count - st.session_state.capture_start_count
    capture_running = sync_native_capture_state(st.session_state)

    should_open = st.session_state.pop("native_capture_should_open", False)
    if person_key and not capture_running and should_open:
        start_native_capture_session(
            st.session_state,
            camera_index=int(st.session_state.get("cam_source", 0)),
            person_key=person_key,
            start_index=current_count,
            profile=DEFAULT_CAMERA_PROFILE,
        )
        capture_running = True

    st.info(
        f"Camera dang ky dang chay bang cua so OpenCV native. "
        f"Bam SPACE trong cua so camera de luu anh dat chat luong, Q/ESC de dong. "
        f"Can toi thieu {MIN_CAPTURE_IMAGES} anh hop le, khuyen nghi {RECOMMENDED_CAPTURE_IMAGES} anh."
    )

    frame_placeholder.markdown(
        f"""
        <div class="zuzo-card" style="min-height:220px;display:flex;align-items:center;justify-content:center;">
            <div style="text-align:center;color:var(--on-surface-variant);font-weight:600;">
                Camera dang ky native {'dang chay' if capture_running else 'da dong'}.<br/>
                Dang chup: {person_key}<br/>
                Anh moi hop le: {valid_count}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not capture_running:
        if st.button("Mo lai camera dang ky", key="btn_restart_native_capture", use_container_width=True):
            start_native_capture_session(
                st.session_state,
                camera_index=int(st.session_state.get("cam_source", 0)),
                person_key=person_key,
                start_index=get_existing_count(person_key),
                profile=DEFAULT_CAMERA_PROFILE,
            )
            st.rerun()
            
    if st.button("Hoan tat & Luu", key="btn_finish_cap", use_container_width=True):
        current_count = get_existing_count(person_key)
        new_valid_count = current_count - st.session_state.capture_start_count
        if not can_finalize_capture(new_valid_count):
            st.warning(f"Can it nhat {MIN_CAPTURE_IMAGES} anh hop le. Hien moi co {new_valid_count}.")
        elif current_count > 0:
            stop_native_capture_session(st.session_state)
            with st.spinner("Dang trich xuat du lieu..."):
                result = finalize_face_registration(person_key)
                if result.ok:
                    st.session_state.db = reload_db()
                    reset_trackers()
                    st.success(result.message)
                else:
                    st.error(result.message)
            _reset_capture_state()
            st.rerun()


def render_face_registration_tab(student_service: StudentService, user_role, default_class_id):
    """Renders the face registration tab where users can add faces to student profiles."""
    if not st.session_state.get("capture_mode"):
        add_mode = st.radio(
            "Cach them", ["Tu UNKNOWN", "Nhap ten moi/cu"],
            horizontal=True, key="add_mode", label_visibility="collapsed"
        )
        if add_mode == "Tu UNKNOWN":
            students_df = student_service.get_all_students()
            unknown_students = students_df[students_df["db_key"].isna()]
            if not unknown_students.empty:
                options = {
                    f"{row['mssv']} - {row['full_name']}": row
                    for _, row in unknown_students.iterrows()
                }
                selected = st.selectbox("Chon SV", list(options.keys()), key="unknown_sv")
                student_row = options[selected]
                suggested_key = student_row["full_name"].replace(" ", "_")
                db_key = st.text_input("DB key", value=suggested_key, key="db_key_input")
                
                if st.button("Bat dau chup", key="btn_capture_unknown", use_container_width=True):
                    if not can_perform(user_role, "face.register"):
                        st.warning("Vai tro hien tai khong co quyen dang ky khuon mat.")
                        return
                        
                    if db_key.strip():
                        student_service.link_student_face(student_row["mssv"], db_key.strip())
                        _begin_capture(db_key.strip())
                        st.rerun()
            else:
                st.caption("Khong co SV UNKNOWN.")
        else:
            new_key = st.text_input("Ten (dung _)", placeholder="VD: Nguyen_Van_A", key="new_key")
            if st.button("Bat dau chup", key="btn_capture_new", use_container_width=True):
                if not can_perform(user_role, "face.register"):
                    st.warning("Vai tro hien tai khong co quyen dang ky khuon mat.")
                    return
                    
                person_key = new_key.strip()
                if person_key:
                    selected_class_id = st.session_state.get("selected_class_id")
                    if selected_class_id is None:
                        selected_class_id = default_class_id
                        
                    student_service.ensure_student_in_class(
                        selected_class_id,
                        full_name=person_key.replace("_", " "),
                        db_key=person_key,
                    )
                    _begin_capture(person_key)
                    st.rerun()
    else:
        current_count = get_existing_count(st.session_state.capture_person_key)
        st.session_state.captured_count = current_count
        st.warning(f"Dang chup: {st.session_state.capture_person_key}")
        st.caption(f"Da chup: {current_count} anh")
        valid_count = current_count - st.session_state.capture_start_count
        st.caption(capture_progress_text(valid_count))
        st.caption(f"Bi tu choi: {st.session_state.capture_rejected_count}")
        if st.session_state.get("last_quality_message"):
            st.caption(st.session_state.last_quality_message)
            
        if st.button("Huy", key="btn_cancel_capture", use_container_width=True):
            stop_native_capture_session(st.session_state)
            clear_person_data(st.session_state.capture_person_key)
            _reset_capture_state()
            st.rerun()
