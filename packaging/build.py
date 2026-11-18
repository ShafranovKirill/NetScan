"""Build the frozen app and icons; run from repository root."""
import argparse
import importlib.metadata
import os
from pathlib import Path
import shutil
import subprocess
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

parser = argparse.ArgumentParser()
parser.add_argument("--onefile", action="store_true")
args = parser.parse_args()
app = QGuiApplication([])
out = Path("build/icons")
out.mkdir(parents=True, exist_ok=True)
image = QImage(256, 256, QImage.Format.Format_ARGB32)
image.fill(0)
painter = QPainter(image)
QSvgRenderer("packaging/netscan.svg").render(painter)
painter.end()
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
           "--add-data", f"packaging/netscan.svg{os.pathsep}.",
           "--add-data", f"LICENSE{os.pathsep}.",
           "--add-data", f"packaging/THIRD_PARTY.md{os.pathsep}.",
           "--add-data", f"{licenses}{os.pathsep}THIRD_PARTY_LICENSES",
           "packaging/entry.py"]
subprocess.run(command, check=True)
