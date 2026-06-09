"""Benchmark native camera profiles for smoothness and clarity."""

import argparse
import os
import statistics
import sys
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.camera_profiles import CAMERA_PROFILES, DEFAULT_CAMERA_PROFILE, resolve_camera_profile


def _decode_fourcc(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return ""
    return "".join(chr((value >> 8 * index) & 0xFF) for index in range(4)).strip("\x00")


def _mean(values):
    return statistics.fmean(values) if values else 0.0


def _open_capture(cv2, camera_index, profile):
    if os.name == "nt":
        cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*profile.fourcc))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, profile.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, profile.height)
    cap.set(cv2.CAP_PROP_FPS, profile.fps)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def measure_capture_profile(cv2, profile, camera_index=0, duration=4.0, warmup=0.5):
    cap = _open_capture(cv2, camera_index, profile)
    result = {
        "profile": profile.name,
        "requested": f"{profile.width}x{profile.height}@{profile.fps}",
        "requested_fourcc": profile.fourcc,
    }
    try:
        if not cap.isOpened():
            result["error"] = f"cannot open camera index {camera_index}"
            return result

        result.update(
            {
                "actual_width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "actual_height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                "actual_fps": float(cap.get(cv2.CAP_PROP_FPS)),
                "actual_fourcc": _decode_fourcc(cap.get(cv2.CAP_PROP_FOURCC)),
            }
        )

        warmup_until = time.monotonic() + warmup
        end_at = warmup_until + duration
        measure_started = None
        measure_finished = None
        frame_count = 0
        read_ms = []
        sharpness = []
        brightness = []

        while time.monotonic() < end_at:
            read_started = time.monotonic()
            ok, frame = cap.read()
            read_finished = time.monotonic()
            if not ok:
                continue
            if read_finished < warmup_until:
                continue

            if measure_started is None:
                measure_started = read_finished
            measure_finished = read_finished
            frame_count += 1
            read_ms.append((read_finished - read_started) * 1000.0)

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            sharpness.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
            brightness.append(float(gray.mean()))

        elapsed = (
            max(0.001, measure_finished - measure_started)
            if measure_started is not None and measure_finished is not None
            else 0.0
        )
        result.update(
            {
                "frames": frame_count,
                "elapsed_seconds": round(elapsed, 3),
                "measured_fps": round(frame_count / elapsed, 2) if elapsed else 0.0,
                "avg_read_ms": round(_mean(read_ms), 2),
                "avg_sharpness": round(_mean(sharpness), 2),
                "avg_brightness": round(_mean(brightness), 2),
            }
        )
        return result
    finally:
        cap.release()


def recommend_profile(results, target_fps=24.0):
    usable = [result for result in results if "error" not in result]
    if not usable:
        return None

    smooth_enough = [
        result for result in usable if float(result.get("measured_fps", 0.0)) >= target_fps
    ]
    if smooth_enough:
        return max(
            smooth_enough,
            key=lambda result: (
                float(result.get("avg_sharpness", 0.0)),
                float(result.get("actual_width", 0.0)) * float(result.get("actual_height", 0.0)),
                float(result.get("measured_fps", 0.0)),
            ),
        )
    return max(usable, key=lambda result: float(result.get("measured_fps", 0.0)))


def _print_table(results):
    headers = [
        "profile",
        "requested",
        "actual",
        "fourcc",
        "fps",
        "read_ms",
        "sharpness",
        "brightness",
        "frames",
    ]
    print(" | ".join(headers))
    print(" | ".join("-" * len(header) for header in headers))
    for result in results:
        if "error" in result:
            print(
                " | ".join(
                    [
                        result["profile"],
                        result.get("requested", ""),
                        "ERROR",
                        "",
                        "0",
                        "",
                        "",
                        "",
                        result["error"],
                    ]
                )
            )
            continue

        actual = f"{result['actual_width']}x{result['actual_height']}@{result['actual_fps']:.1f}"
        print(
            " | ".join(
                [
                    result["profile"],
                    result["requested"],
                    actual,
                    result.get("actual_fourcc") or result.get("requested_fourcc", ""),
                    f"{result.get('measured_fps', 0.0):.2f}",
                    f"{result.get('avg_read_ms', 0.0):.2f}",
                    f"{result.get('avg_sharpness', 0.0):.2f}",
                    f"{result.get('avg_brightness', 0.0):.2f}",
                    str(result.get("frames", 0)),
                ]
            )
        )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Benchmark native camera profiles.")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--duration", type=float, default=4.0)
    parser.add_argument("--warmup", type=float, default=0.5)
    parser.add_argument(
        "--profiles",
        nargs="*",
        choices=list(CAMERA_PROFILES),
        default=list(CAMERA_PROFILES),
    )
    parser.add_argument("--target-fps", type=float, default=24.0)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    import cv2

    results = [
        measure_capture_profile(
            cv2,
            resolve_camera_profile(profile_name),
            camera_index=args.camera_index,
            duration=args.duration,
            warmup=args.warmup,
        )
        for profile_name in args.profiles
    ]
    _print_table(results)

    recommendation = recommend_profile(results, target_fps=args.target_fps)
    if recommendation is None:
        print(f"\nRecommended profile: {DEFAULT_CAMERA_PROFILE} (no usable camera results)")
    else:
        print(
            "\nRecommended profile: "
            f"{recommendation['profile']} "
            f"({recommendation.get('measured_fps', 0.0):.2f} FPS, "
            f"sharpness {recommendation.get('avg_sharpness', 0.0):.2f})"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
