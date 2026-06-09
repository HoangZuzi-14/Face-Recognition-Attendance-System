"""Manage the native OpenCV attendance camera process from Streamlit."""

import os
import subprocess
import sys
from pathlib import Path

from app.camera_profiles import DEFAULT_CAMERA_PROFILE, resolve_camera_profile

PROCESS_KEY = "native_camera_process"


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


def _popen_kwargs():
    kwargs = {
        "cwd": str(_repo_root()),
        "stdin": subprocess.DEVNULL,
    }
    if os.name == "nt" and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    return kwargs


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

    command = build_native_camera_command(
        camera_index=camera_index,
        class_id=class_id,
        deadline_hour=deadline_hour,
        deadline_minute=deadline_minute,
        profile=profile,
    )
    process = popen(command, **_popen_kwargs())
    session_state[PROCESS_KEY] = process
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
    return stopped


def sync_native_camera_state(session_state):
    process = session_state.get(PROCESS_KEY)
    running = is_process_running(process)
    if not running:
        session_state[PROCESS_KEY] = None
        session_state["run"] = False
    else:
        session_state["run"] = True
    return running
