import os
import sys
import zipfile
from pathlib import Path

EXCLUDE_PREFIXES = (
    ".git/",
    ".git\\",
    ".venv/",
    ".venv\\",
    "venv/",
    "venv\\",
)


def should_exclude(name: str) -> bool:
    normalized = name.replace("\\", "/")
    return normalized.startswith(EXCLUDE_PREFIXES)


def rewrite_zip(zip_path: Path) -> None:
    tmp_path = zip_path.with_suffix(zip_path.suffix + ".tmp")
    with zipfile.ZipFile(zip_path, "r") as zin, zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            if should_exclude(item.filename):
                continue
            data = zin.read(item.filename)
            zout.writestr(item, data)
    tmp_path.replace(zip_path)


def find_app_zips(root: Path) -> list[Path]:
    return [p for p in root.rglob("app.zip") if p.is_file()]


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    zips = find_app_zips(root)
    if not zips:
        print("No app.zip found")
        return 0
    for zp in zips:
        rewrite_zip(zp)
        print(f"Stripped: {zp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
