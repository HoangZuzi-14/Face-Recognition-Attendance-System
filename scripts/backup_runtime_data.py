import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


DEFAULT_INCLUDE_PATHS = [
    "app/attendance.db",
    "data/embeddings/db.pkl",
    "data/raw",
    "data/processed",
    "app/config.py",
    "app/camera_profiles.py",
    "src/face_db.py",
]


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_source(project_root, relative_path):
    source = (project_root / relative_path).resolve()
    root = project_root.resolve()
    if source != root and root not in source.parents:
        raise ValueError(f"Path escapes project root: {relative_path}")
    return source


def _unique_backup_dir(backup_root, timestamp):
    candidate = backup_root / timestamp
    if not candidate.exists():
        return candidate
    suffix = 1
    while True:
        candidate = backup_root / f"{timestamp}_{suffix:02d}"
        if not candidate.exists():
            return candidate
        suffix += 1


def _copy_file(project_root, backup_dir, source, manifest_files):
    relative = source.resolve().relative_to(project_root.resolve())
    target = backup_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    stat = target.stat()
    manifest_files.append(
        {
            "relative_path": relative.as_posix(),
            "size_bytes": stat.st_size,
            "backed_up_at": datetime.now().isoformat(),
            "sha256": _sha256(target),
        }
    )


def create_runtime_backup(
    project_root=".",
    backup_root=None,
    timestamp=None,
    include_paths=None,
):
    project_root = Path(project_root).resolve()
    backup_root = Path(backup_root) if backup_root is not None else project_root / "backups"
    if not backup_root.is_absolute():
        backup_root = project_root / backup_root
    backup_root.mkdir(parents=True, exist_ok=True)

    backup_dir = _unique_backup_dir(backup_root, timestamp or _timestamp())
    backup_dir.mkdir(parents=True, exist_ok=False)

    manifest = {
        "created_at": datetime.now().isoformat(),
        "project_root": str(project_root),
        "backup_dir": str(backup_dir),
        "files": [],
        "missing": [],
    }

    for relative_path in include_paths or DEFAULT_INCLUDE_PATHS:
        source = _safe_source(project_root, relative_path)
        if not source.exists():
            manifest["missing"].append(str(relative_path))
            continue
        if source.is_dir():
            for file_path in sorted(path for path in source.rglob("*") if path.is_file()):
                _copy_file(project_root, backup_dir, file_path, manifest["files"])
        else:
            _copy_file(project_root, backup_dir, source, manifest["files"])

    manifest_path = backup_dir / "backup_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)

    return backup_dir, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description="Back up Face_attendance runtime data.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--backup-root", default=None)
    args = parser.parse_args(argv)

    backup_dir, manifest = create_runtime_backup(
        project_root=args.project_root,
        backup_root=args.backup_root,
    )
    print(f"Backup created: {backup_dir}")
    print(f"Files copied: {len(manifest['files'])}")
    if manifest["missing"]:
        print("Missing paths:")
        for path in manifest["missing"]:
            print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
