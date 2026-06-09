import json
import shutil
import hashlib
from datetime import datetime
from pathlib import Path


DEFAULT_BACKUP_ROOT = Path("backups")
DEFAULT_MAX_BACKUP_DIRS = 30


def _timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _file_checksum(path, algo="sha256"):
    """Compute a file checksum for integrity verification."""
    h = hashlib.new(algo)
    try:
        with open(path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _prune_backup_dirs(backup_root=DEFAULT_BACKUP_ROOT, max_dirs=DEFAULT_MAX_BACKUP_DIRS):
    root = Path(backup_root)
    if max_dirs is None or max_dirs <= 0 or not root.exists():
        return
    dirs = sorted([path for path in root.iterdir() if path.is_dir()])
    for old_dir in dirs[:-max_dirs]:
        shutil.rmtree(old_dir, ignore_errors=True)


def backup_file(source_path, backup_root=DEFAULT_BACKUP_ROOT, label=None, max_dirs=DEFAULT_MAX_BACKUP_DIRS):
    """Copy an existing file into backups and return the backup path."""
    source = Path(source_path)
    if not source.exists():
        return None

    backup_dir = Path(backup_root) / _timestamp()
    backup_dir.mkdir(parents=True, exist_ok=True)

    prefix = f"{label}_" if label else ""
    target = backup_dir / f"{prefix}{source.name}"
    shutil.copy2(source, target)

    # Write manifest
    manifest = {
        "created_at": datetime.now().isoformat(),
        "source_path": str(source),
        "backup_path": str(target),
        "label": label,
        "checksum": {
            source.name: _file_checksum(target),
        },
    }
    manifest_path = backup_dir / "manifest.json"
    # Merge with existing manifest if backup_dir already has one
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if "files" not in existing:
                existing["files"] = []
            existing["files"].append(manifest)
            manifest = existing
        except (json.JSONDecodeError, OSError):
            manifest = {"files": [manifest]}
    else:
        manifest = {"created_at": manifest["created_at"], "files": [manifest]}

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    _prune_backup_dirs(backup_root, max_dirs=max_dirs)
    return target


def backup_face_db(face_db_path="data/embeddings/db.pkl", backup_root=DEFAULT_BACKUP_ROOT):
    return backup_file(face_db_path, backup_root=backup_root, label="face_db")


def backup_sqlite_db(sql_db_path="app/attendance.db", backup_root=DEFAULT_BACKUP_ROOT):
    return backup_file(sql_db_path, backup_root=backup_root, label="attendance")


def list_backups(backup_root=DEFAULT_BACKUP_ROOT):
    """List all backup directories with their manifests, newest first."""
    root = Path(backup_root)
    if not root.exists():
        return []
    results = []
    for d in sorted(root.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        manifest_path = d / "manifest.json"
        manifest = None
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        files = list(d.glob("*"))
        results.append({
            "dir": str(d),
            "name": d.name,
            "manifest": manifest,
            "files": [str(fp) for fp in files if fp.name != "manifest.json"],
        })
    return results


def restore_backup(backup_dir_path, target_dir=None):
    """Restore files from a backup directory to their original locations.

    Args:
        backup_dir_path: Path to the backup directory (e.g. 'backups/20260525_185624_101145')
        target_dir: If provided, restore all files to this directory instead of
                     their original source paths.

    Returns:
        A list of (backup_file, restored_to) tuples for each restored file,
        or an error string if something went wrong.
    """
    backup_dir = Path(backup_dir_path)
    if not backup_dir.is_dir():
        return f"Backup directory not found: {backup_dir}"

    manifest_path = backup_dir / "manifest.json"
    manifest = None
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    restored = []

    if manifest and "files" in manifest:
        # Manifest-guided restore: use original source paths
        for entry in manifest["files"]:
            backup_file_path = Path(entry.get("backup_path", ""))
            source_path = Path(entry.get("source_path", ""))

            if not backup_file_path.exists():
                # Try finding the file in the backup dir by name
                backup_file_path = backup_dir / backup_file_path.name
            if not backup_file_path.exists():
                continue

            # Verify checksum if available
            checksums = entry.get("checksum", {})
            for fname, expected in checksums.items():
                actual = _file_checksum(backup_file_path)
                if expected and actual and expected != actual:
                    return f"Checksum mismatch for {fname}: expected {expected[:12]}..., got {actual[:12]}..."

            restore_to = Path(target_dir) / backup_file_path.name if target_dir else source_path
            restore_to.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_file_path, restore_to)
            restored.append((str(backup_file_path), str(restore_to)))
    else:
        # No manifest: restore all non-manifest files
        for fp in backup_dir.iterdir():
            if fp.name == "manifest.json" or fp.is_dir():
                continue
            if target_dir:
                restore_to = Path(target_dir) / fp.name
            else:
                # Without manifest we don't know original paths; put next to backup
                return f"No manifest found in {backup_dir}. Cannot determine original paths. Use target_dir argument."
            restore_to.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fp, restore_to)
            restored.append((str(fp), str(restore_to)))

    return restored
