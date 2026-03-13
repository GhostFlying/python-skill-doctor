from __future__ import annotations

import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


EXCLUDE_DIRS = {"__pycache__", ".git", ".venv"}
EXCLUDE_SUFFIXES = {".pyc"}
EXCLUDE_FILES = {".DS_Store"}


def should_include(path: Path) -> bool:
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return False
    if path.name in EXCLUDE_FILES:
        return False
    if path.suffix in EXCLUDE_SUFFIXES:
        return False
    return True


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    output = root.parent / f"{root.name}.skill"

    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if path.is_dir() or not should_include(path):
                continue
            archive.write(path, arcname=path.relative_to(root))

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
