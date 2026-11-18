"""Build the frozen app and icons; run from repository root."""
import argparse
import importlib.metadata
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtGui import QGuiApplication, QImage
from PySide6.QtCore import Qt

parser = argparse.ArgumentParser()
parser.add_argument("--onefile", action="store_true")
args = parser.parse_args()
app = QGuiApplication([])
out = Path("build/icons")
out.mkdir(parents=True, exist_ok=True)
image = QImage("packaging/netscan.png")
if image.isNull():
    raise RuntimeError("Application logo is missing or invalid")
image = image.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
image.save(str(out / "netscan.png"))
image.save(str(out / "netscan.ico"))
licenses = Path("build/THIRD_PARTY_LICENSES")
licenses.mkdir(parents=True, exist_ok=True)
for distribution in importlib.metadata.distributions():
    for file in distribution.files or []:
        if any(part.lower() in {"licenses", "license", "copying"} for part in file.parts) or file.name.lower().startswith(("license", "copying")):
            source = Path(distribution.locate_file(file))
            if source.is_file():
                target = licenses / distribution.metadata["Name"] / str(file).replace("..", "_")
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
           "--name", "NetScan", "--windowed", "--paths", ".",
           "--onefile" if args.onefile else "--onedir",
           "--icon", str(out / "netscan.ico"),
           "--add-data", f"packaging/netscan.png{os.pathsep}.",
           "--add-data", f"LICENSE{os.pathsep}.",
           "--add-data", f"packaging/THIRD_PARTY.md{os.pathsep}.",
           "--add-data", f"{licenses}{os.pathsep}THIRD_PARTY_LICENSES",
           "--copy-metadata", "keyring",
           "--hidden-import", "keyring.backends.Windows" if sys.platform == "win32" else "keyring.backends.SecretService",
           "packaging/entry.py"]
if sys.platform == "win32":
    version = importlib.metadata.version("netscan-desktop")
    numeric = tuple(int(part) for part in re.match(r"(\d+)\.(\d+)\.(\d+)", version).groups()) + (0,)
    resource = out / "version.txt"
    resource.write_text(
        "VSVersionInfo(ffi=FixedFileInfo(filevers=" + repr(numeric) +
        ", prodvers=" + repr(numeric) +
        ", mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)), "
        "kids=[StringFileInfo([StringTable('040904B0', ["
        "StringStruct('CompanyName', 'Kirill Shafranov'), "
        "StringStruct('FileDescription', 'NetScan desktop proxy scanner'), "
        "StringStruct('FileVersion', " + repr(version) + "), "
        "StringStruct('ProductName', 'NetScan'), "
        "StringStruct('ProductVersion', " + repr(version) + ")])]), "
        "VarFileInfo([VarStruct('Translation', [1033, 1200])])])", encoding="utf-8")
    command.extend(["--version-file", str(resource)])
subprocess.run(command, check=True)
