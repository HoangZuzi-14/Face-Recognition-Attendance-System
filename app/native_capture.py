"""Manage the native OpenCV face-registration capture process from Streamlit."""

import os
import subprocess
import sys
from pathlib import Path

from app.camera_profiles import DEFAULT_CAMERA_PROFILE, resolve_camera_profile


PROCESS_KEY = "native_capture_process"
PERSON_KEY = "native_capture_person_key"


def _repo_root():
    return Path(__file__).resolve().parents[1]


def build_native_capture_command(
    python_executable=None,
    camera_index=0,
    person_key="",
    start_index=0,
    profile=DEFAULT_CAMERA_PROFILE,
):
    camera_profile = resolve_camera_profile(profile)
    return [
        python_executable or sys.executable,
        "-m",
        "app.native_capture_runner",
        "--camera-index",
        str(int(camera_index)),
        "--person-key",
        str(person_key),
        "--start-index",
        str(int(start_index)),
        "--profile",
        camera_profile.name,
    ]


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


def start_native_capture_session(
    session_state,
    camera_index=0,
    person_key="",
    start_index=0,
    profile=DEFAULT_CAMERA_PROFILE,
    popen=subprocess.Popen,
):
    existing = session_state.get(PROCESS_KEY)
    if is_process_running(existing):
        if session_state.get(PERSON_KEY) == str(person_key):
            return existing
        stop_native_capture_session(session_state)

    command = build_native_capture_command(
        camera_index=camera_index,
        person_key=person_key,
        start_index=start_index,
        profile=profile,
    )
    process = popen(command, **_popen_kwargs())
    session_state[PROCESS_KEY] = process
    session_state[PERSON_KEY] = str(person_key)
    session_state["native_capture_command"] = " ".join(command)
    return process


def stop_native_capture_session(session_state):
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
    session_state[PERSON_KEY] = None
    return stopped


def sync_native_capture_state(session_state):
    process = session_state.get(PROCESS_KEY)
    running = is_process_running(process)
    if not running:
        session_state[PROCESS_KEY] = None
        session_state[PERSON_KEY] = None
    return running
