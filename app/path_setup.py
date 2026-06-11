import os
import sys
from pathlib import Path


def find_repo_root(current_file):
    path = Path(current_file).resolve()
    for parent in [path.parent, *path.parents]:
        if (parent / "app").is_dir() and (parent / "services").is_dir():
            return str(parent)
    return os.path.abspath(os.path.join(os.path.dirname(str(path)), ".."))


def ensure_repo_root_first(current_file, path_list=None):
    paths = sys.path if path_list is None else path_list
    repo_root = find_repo_root(current_file)

    while repo_root in paths:
        paths.remove(repo_root)
    paths.insert(0, repo_root)

    return repo_root
