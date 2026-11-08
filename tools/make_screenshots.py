"""Capture the README screenshots from the real app window, using the synthetic demo photos.

Usage:  python tools/make_demo_photos.py          (once, creates docs/demo-photos)
        python tools/make_screenshots.py          (writes docs/screenshots/*.png)

Loading and culling are slowed down artificially so the progress counts can be captured mid-run.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402
from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from culler import analysis, ui  # noqa: E402

DEMO = ROOT / "docs" / "demo-photos"
OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

app = QApplication([])
app.setStyle("Fusion")
app.setStyleSheet(ui.QSS)
w = ui.MainWindow()
w.resize(1440, 860)
w.show()
w._offer_restore = lambda: None  # never prompt for a saved session while taking screenshots

_real_load, _real_analyze = analysis.load_photo, analysis.analyze_photo


def _slow(fn, delay):
    def wrapped(*a, **k):
        time.sleep(delay)
        return fn(*a, **k)
    return wrapped


def shot(name: str):
    app.processEvents()
    path = OUT / name
    w.grab().save(str(path))
    img = Image.open(path).convert("RGB")  # normalise to 1440 px wide whatever the display scaling was
    if img.width != 1440:
        img = img.resize((1440, round(img.height * 1440 / img.width)), Image.LANCZOS)
    img.save(path, optimize=True)
    print("saved", name, f"({path.stat().st_size // 1024} KB)")


def wait_for(cond, then, every=40):
    def tick():
        if cond():
            then()
        else:
            QTimer.singleShot(every, tick)
    tick()


def select_photo(name: str):
    for i in range(w.list.count()):
        if w.list.item(i).data(ui.Qt.UserRole).name == name:
            w.list.setCurrentRow(i)
            return


def pick(tab: str):
    w.tab_btns[tab].click()
    app.processEvents()


def step_start():
    shot("01-start.png")
    analysis.load_photo = _slow(_real_load, 0.35)
    w.load_folder(DEMO)
    wait_for(lambda: w.progress.value() >= w.progress.maximum() * 0.55, step_loading)


def step_loading():
    shot("02-loading.png")
    analysis.load_photo = _real_load
    wait_for(lambda: w.state == "loaded", step_loaded)


def step_loaded():
    w.list.setCurrentRow(3)
    shot("03-loaded.png")
    analysis.analyze_photo = _slow(_real_analyze, 0.5)
    w.start_culling()
    wait_for(lambda: w.progress.value() >= w.progress.maximum() * 0.5, step_culling)


def step_culling():
    shot("04-culling.png")
    analysis.analyze_photo = _real_analyze
    wait_for(lambda: w.state == "results", step_results)


def step_results():
    select_photo("DEMO0013")
    shot("05-results.png")
    pick("reject")
    select_photo("DEMO0012")
    shot("06-rejects.png")
    pick("dup")
    select_photo("DEMO0014")
    w.preview.set_zoom(2.2)
    shot("07-duplicates-zoom.png")
    w.preview.set_zoom(1.0)
    pick("keep")
    select_photo("DEMO0009")
    shot("08-keep.png")
    w._dirty = False
    app.quit()


QTimer.singleShot(200, step_start)
app.exec()
