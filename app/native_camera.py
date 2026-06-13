"""Manage the native OpenCV attendance camera process from Streamlit."""

import os
import subprocess
import sys
from pathlib import Path

from app.config import FACE_DB_PATH, LIVENESS_ENABLED
from app.camera_profiles import DEFAULT_CAMERA_PROFILE, resolve_camera_profile
from src.face_db import identity_count

PROCESS_KEY = "native_camera_process"
LOG_HANDLE_KEY = "native_camera_log_handle"
LOG_PATH_KEY = "native_camera_log_path"
PREFLIGHT_KEY = "native_camera_preflight"
ERROR_KEY = "native_camera_error"
DEFAULT_LOG_PATH = Path("logs/native_camera.log")


def _repo_root():
    return Path(__file__).resolve().parents[1]


def build_native_camera_command(
    python_executable=None,
    camera_index=0,
    class_id=None,
    deadline_hour=8,
    deadline_minute=0,
    profile=DEFAULT_CAMERA_PROFILE,
):
    camera_profile = resolve_camera_profile(profile)
    command = [
        python_executable or sys.executable,
        "-m",
        "app.native_camera_runner",
        "--camera-index",
        str(int(camera_index)),
        "--profile",
        camera_profile.name,
        "--deadline-hour",
        str(int(deadline_hour)),
        "--deadline-minute",
        str(int(deadline_minute)),
    ]
    if class_id is not None:
        command.extend(["--class-id", str(int(class_id))])
    return command


def is_process_running(process):
    return process is not None and process.poll() is None


def _log_path():
    path = _repo_root() / DEFAULT_LOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _open_log_handle():
    path = _log_path()
    handle = path.open("a", encoding="utf-8", buffering=1)
    handle.write("\n--- native camera session start ---\n")
    return path, handle


def _close_log_handle(session_state):
    handle = session_state.get(LOG_HANDLE_KEY)
    if handle is not None:
        try:
            handle.flush()
            handle.close()
        except Exception:
            pass
    session_state[LOG_HANDLE_KEY] = None


def _popen_kwargs(log_handle=None):
    kwargs = {
        "cwd": str(_repo_root()),
        "stdin": subprocess.DEVNULL,
    }
    if log_handle is not None:
        kwargs["stdout"] = log_handle
        kwargs["stderr"] = subprocess.STDOUT
    if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    return kwargs


def describe_native_camera_exit(returncode):
    messages = {
        2: "Face DB not found. Build data/embeddings/db.pkl first.",
        3: "No usable face embeddings for the selected class.",
        4: "Cannot open the selected camera index.",
    }
    return messages.get(returncode, f"Native camera exited with code {returncode}.")


def get_native_camera_preflight(
    class_id=None,
    db_loader=None,
    active_db_builder=None,
    sqlite_db_path="app/attendance.db",
    face_db_path=FACE_DB_PATH,
    liveness_enabled=None,
):
    if db_loader is None:
        from src.recognize import load_db

        db_loader = load_db
    if active_db_builder is None:
        from services.recognition_service import RecognitionService

        active_db_builder = RecognitionService().build_active_face_db

    try:
        db = db_loader()
        face_db_status = "available" if db else "missing"
        active_db = active_db_builder(db, class_id) if db and class_id is not None else db
        active_identity_count = identity_count(active_db or {})
    except Exception as exc:
        db = None
        face_db_status = f"error: {exc}"
        active_identity_count = 0

    sqlite_status = "available" if Path(sqlite_db_path).exists() else "missing"
    return {
        "active_identity_count": active_identity_count,
        "face_db_status": face_db_status,
        "face_db_path": face_db_path,
        "sqlite_status": sqlite_status,
        "sqlite_db_path": sqlite_db_path,
        "liveness_enabled": LIVENESS_ENABLED if liveness_enabled is None else bool(liveness_enabled),
    }


def start_native_camera_session(
    session_state,
    camera_index=0,
    class_id=None,
    deadline_hour=8,
    deadline_minute=0,
    profile=DEFAULT_CAMERA_PROFILE,
    popen=subprocess.Popen,
):
    existing = session_state.get(PROCESS_KEY)
    if is_process_running(existing):
        session_state["run"] = True
        return existing

    session_state.pop(ERROR_KEY, None)
    _close_log_handle(session_state)
    preflight = get_native_camera_preflight(class_id=class_id)
    session_state[PREFLIGHT_KEY] = preflight
    log_path, log_handle = _open_log_handle()
    command = build_native_camera_command(
        camera_index=camera_index,
        class_id=class_id,
        deadline_hour=deadline_hour,
        deadline_minute=deadline_minute,
        profile=profile,
    )
    process = popen(command, **_popen_kwargs(log_handle))
    stored_log_handle = log_handle
    if not isinstance(process, subprocess.Popen):
        # Unit-test fakes do not own the file descriptor the way Popen does.
        # Close immediately after kwargs capture to avoid leaking handles.
        try:
            log_handle.flush()
            log_handle.close()
        except Exception:
            pass
        stored_log_handle = None
    session_state[PROCESS_KEY] = process
    session_state[LOG_HANDLE_KEY] = stored_log_handle
    session_state[LOG_PATH_KEY] = str(log_path.relative_to(_repo_root()))
    session_state["native_camera_command"] = " ".join(command)
    session_state["run"] = True
    return process


def stop_native_camera_session(session_state):
    process = session_state.get(PROCESS_KEY)
    stopped = False
    if is_process_running(process):
        try:
            process.terminate()
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            stopped = True
        else:
            stopped = True

    session_state[PROCESS_KEY] = None
    session_state["run"] = False
    _close_log_handle(session_state)
    return stopped


def sync_native_camera_state(session_state):
    process = session_state.get(PROCESS_KEY)
    returncode = process.poll() if process is not None else None
    running = process is not None and returncode is None
    if not running:
        if process is not None and returncode not in (None, 0):
            log_path = session_state.get(LOG_PATH_KEY, str(DEFAULT_LOG_PATH))
            session_state[ERROR_KEY] = (
                f"{describe_native_camera_exit(returncode)} See log: {log_path}"
            )
        session_state[PROCESS_KEY] = None
        session_state["run"] = False
        _close_log_handle(session_state)
    else:
        session_state["run"] = True
    return running
