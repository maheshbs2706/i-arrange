"""Build a versioned i-arrange exe.

Usage:  python build.py [--current | patch | minor | major | same | X.Y.Z]
Output: dist/i-arrange-v<version>.exe
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION_FILE = ROOT / "VERSION"
VERSION_PY = ROOT / "culler" / "_version.py"
BUILD_DIR = ROOT / "build"


def current() -> str:
    return VERSION_FILE.read_text().strip() if VERSION_FILE.exists() else "0.1.0"


def resolve(arg: str) -> str:
    cur = current()
    if arg == "same":
        return cur
    if arg in ("patch", "minor", "major"):
        ma, mi, pa = (int(x) for x in cur.split("."))
        return {"patch": f"{ma}.{mi}.{pa + 1}", "minor": f"{ma}.{mi + 1}.0", "major": f"{ma + 1}.0.0"}[arg]
    if re.fullmatch(r"\d+\.\d+\.\d+", arg):
        return arg
    sys.exit(f"Invalid version '{arg}'. Use patch, minor, major, same or X.Y.Z (e.g. 1.2.0).")


def version_info(v: str) -> str:
    t = tuple(int(x) for x in v.split(".")) + (0,)
    return f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={t}, prodvers={t}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('FileDescription', 'i-arrange'),
      StringStruct('FileVersion', '{v}'),
      StringStruct('InternalName', 'i-arrange'),
      StringStruct('OriginalFilename', 'i-arrange-v{v}.exe'),
      StringStruct('ProductName', 'i-arrange'),
      StringStruct('ProductVersion', '{v}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else "same"
    if arg == "--current":
        print(current())
        return 0
    v = resolve(arg)
    name = f"i-arrange-v{v}"
    print(f"\n=== Building {name}.exe (version {v}) ===\n")

    BUILD_DIR.mkdir(exist_ok=True)
    info = BUILD_DIR / "version_info.txt"
    info.write_text(version_info(v), encoding="utf-8")

    icon = ROOT / "assets" / "i-arrange.ico"
    if not icon.exists():
        subprocess.run([sys.executable, str(ROOT / "make_icon.py")], cwd=ROOT, check=False)

    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
        "--name", name, "--distpath", str(ROOT / "dist"), "--workpath", str(BUILD_DIR / "work"),
        "--specpath", str(BUILD_DIR), "--version-file", str(info), "--collect-data", "cv2",
        "--add-data", f"{ROOT / 'assets' / 'models'};assets/models",  # face detector model
        *(["--icon", str(icon)] if icon.exists() else []),
        *sum((["--exclude-module", m] for m in (
            "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtPdf",
            "PySide6.QtQuick", "PySide6.QtQml", "PySide6.Qt3DCore")), []),
        str(ROOT / "main.py"),
    ]

    VERSION_PY.write_text(f'__version__ = "{v}"\n')  # baked into the exe
    try:
        rc = subprocess.run(cmd, cwd=ROOT).returncode
    finally:
        VERSION_PY.write_text('__version__ = "dev"\n')  # dev runs show "dev" again
    if rc != 0:
        print("\nBuild FAILED. If the error mentions 'Access is denied', close any running copy of that exe.")
        return rc
    VERSION_FILE.write_text(v + "\n")
    print(f"\nDone: dist\\{name}.exe")
    return 0


if __name__ == "__main__":
    sys.exit(main())
