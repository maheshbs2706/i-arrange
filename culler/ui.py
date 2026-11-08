"""PySide6 desktop UI for i-arrange (dark, card-based design)."""
from __future__ import annotations

import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PySide6.QtCore import QPointF, QRect, QRectF, QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QKeySequence, QPainter, QPainterPath, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QFileDialog, QFrame, QHBoxLayout, QLabel, QListView, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QProgressBar, QProgressDialog, QPushButton, QSizePolicy,
    QSlider, QSplitter, QStyle, QStyledItemDelegate, QToolButton, QVBoxLayout, QWidget,
)

from . import analysis, icons, session
from .analysis import Photo

# ------------------------------------------------------------------ theme
BG, PANEL, CARD, BORDER = "#0e1018", "#131624", "#1b1f31", "#262b42"
TEXT, MUTED = "#e9ebf5", "#8c92ac"
ACCENT, ACCENT2 = "#6366f1", "#8b5cf6"
GREEN, RED, GRAY = "#22c55e", "#ef4444", "#6b7280"

QSS = """
* { font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif; color: @TEXT@; }
QMainWindow, QWidget#root { background: @BG@; }
QFrame#header, QFrame#footer { background: @PANEL@; }
QFrame#header { border-bottom: 1px solid @BORDER@; }
QFrame#footer { border-top: 1px solid @BORDER@; }
QLabel { background: transparent; }
QLabel#appTitle { font-size: 18px; font-weight: 700; }
QLabel#muted { color: @MUTED@; font-size: 12px; }
QLabel#strictVal { font-size: 18px; font-weight: 700; }
QLabel#strictLbl { font-size: 14px; font-weight: 600; }
QFrame#divider { background: @BORDER@; max-width: 1px; min-width: 1px; }
QPushButton#openBtn { background: #232842; border: 1px solid #2f3556; border-radius: 12px;
    padding: 12px 22px; font-size: 14px; font-weight: 600; }
QPushButton#openBtn:hover { background: #2b3050; }
QPushButton#openBtn:disabled { color: #5b6080; }
QToolButton#iconBtn { background: transparent; border: none; border-radius: 16px; padding: 6px; }
QToolButton#iconBtn:hover { background: #20243a; }
QPushButton#pill { background: #171a2b; color: #a3a8c3; border: 1px solid transparent; border-radius: 16px;
    padding: 9px 12px; font-size: 13px; font-weight: 600; }
QPushButton#pill:hover { background: #1e2236; }
QPushButton#pill:checked { background: #2a2d5e; color: #ffffff; border: 1px solid #4a4ec7; }
QListWidget { background: transparent; border: none; outline: none; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #2c3150; border-radius: 4px; min-height: 40px; }
QScrollBar::handle:vertical:hover { background: #3a4066; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QSlider::groove:horizontal { height: 6px; background: #262b42; border-radius: 3px; }
QSlider::sub-page:horizontal { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 @ACCENT@, stop:1 @ACCENT2@);
    border-radius: 3px; }
QSlider::handle:horizontal { background: #ffffff; border: 3px solid @ACCENT@; width: 12px; height: 12px;
    margin: -8px 0; border-radius: 9px; }
QProgressBar#thin { background: transparent; border: none; max-height: 3px; min-height: 3px; }
QProgressBar#thin::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 @ACCENT@, stop:1 @ACCENT2@); }
QPushButton#keepBtn, QPushButton#rejectBtn, QPushButton#dupBtn { border-radius: 10px; padding: 8px 18px;
    font-size: 14px; font-weight: 600; background: transparent; }
QPushButton#keepBtn { border: 1.5px solid @GREEN@; background: rgba(34,197,94,0.10); }
QPushButton#keepBtn:hover { background: rgba(34,197,94,0.22); }
QPushButton#rejectBtn { border: 1.5px solid @RED@; background: rgba(239,68,68,0.10); }
QPushButton#rejectBtn:hover { background: rgba(239,68,68,0.22); }
QPushButton#dupBtn, QPushButton#saveBtn { border: 1.5px solid #3b4160; background: rgba(255,255,255,0.03); }
QPushButton#dupBtn:hover, QPushButton#saveBtn:hover { background: rgba(255,255,255,0.08); }
QPushButton#saveBtn { border-radius: 10px; padding: 8px 18px; font-size: 14px; font-weight: 600; }
QPushButton#saveBtn:disabled { color: #5b6080; border-color: #2a2f45; background: transparent; }
QPushButton#keepBtn:disabled, QPushButton#rejectBtn:disabled, QPushButton#dupBtn:disabled {
    color: #5b6080; border-color: #2a2f45; background: transparent; }
QPushButton#startBtn { border: none; border-radius: 12px; padding: 12px 24px; font-size: 14px; font-weight: 700;
    color: white; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 @ACCENT@, stop:1 @ACCENT2@); }
QPushButton#startBtn:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7478ff, stop:1 #9b73f8); }
QPushButton#startBtn:disabled { background: #232842; color: #5b6080; }
QPushButton#cancelBtn { border: 1.5px solid @RED@; border-radius: 12px; padding: 12px 24px; font-size: 14px;
    font-weight: 700; background: rgba(239,68,68,0.10); }
QPushButton#cancelBtn:hover { background: rgba(239,68,68,0.22); }
QSlider::sub-page:horizontal:disabled { background: #3a3f5e; }
QSlider::handle:horizontal:disabled { border-color: #4a4f70; }
QLabel#strictLbl:disabled, QLabel#strictVal:disabled { color: #5b6080; }
QPushButton#pill:disabled { color: #4d5272; }
QPushButton#exportBtn { border: none; border-radius: 10px; padding: 9px 22px; font-size: 14px; font-weight: 700;
    color: white; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 @ACCENT@, stop:1 @ACCENT2@); }
QPushButton#exportBtn:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7478ff, stop:1 #9b73f8); }
QPushButton#exportBtn:disabled { background: #232842; color: #5b6080; }
QFrame#overlay { background: rgba(14,16,24,200); border: 1px solid rgba(255,255,255,28); border-radius: 14px; }
QFrame#overlay QLabel { background: transparent; }
QToolButton#ovBtn { background: transparent; border: none; padding: 6px; border-radius: 10px; }
QToolButton#ovBtn:hover { background: rgba(255,255,255,25); }
QSplitter::handle { background: transparent; width: 6px; }
"""
for _k, _v in dict(BG=BG, PANEL=PANEL, BORDER=BORDER, TEXT=TEXT, MUTED=MUTED, ACCENT=ACCENT, ACCENT2=ACCENT2,
                   GREEN=GREEN, RED=RED).items():
    QSS = QSS.replace(f"@{_k}@", _v)


def _fmt(n: int) -> str:
    return f"{n:,}"


# ------------------------------------------------------------------ background analysis
class PoolWorker(QThread):
    """Runs fn(*args) for every args-tuple in items on a thread pool, reporting progress as it goes."""
    progress = Signal(int, int)
    finished_ok = Signal(list)

    def __init__(self, fn, items):
        super().__init__()
        self.fn = fn
        self.items = items
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        total = len(self.items)
        results: list[Photo | None] = [None] * total
        done = 0
        with ThreadPoolExecutor(max_workers=max(2, (os.cpu_count() or 4) - 1)) as ex:
            futs = {ex.submit(self.fn, *args): i for i, args in enumerate(self.items)}
            for fut in as_completed(futs):
                if self._cancel:
                    for f in futs:
                        f.cancel()
                    return
                results[futs[fut]] = fut.result()
                done += 1
                self.progress.emit(done, total)
        self.finished_ok.emit([r for r in results if r is not None])


# ------------------------------------------------------------------ thumbnail grid
def _badge_for(p: Photo) -> tuple[str, str]:
    if p.status == "keep":
        return "check", GREEN
    if p.manual:
        return ("copy", GRAY) if p.manual_reason == "duplicate" else ("x", RED)
    r = p.reason
    if "blurry" in r:
        return "alert", RED
    if "exposure" in r:
        return "sun", RED
    if "duplicate" in r:
        return "copy", GRAY
    return "x", RED


class ThumbDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cell = QSize(190, 232)
        self.cache: dict[int, QPixmap] = {}
        self.verdicts = False  # badges / dimming only once culling has finished (state == 'results')

    def sizeHint(self, option, index):
        return self.cell

    def _pix(self, p: Photo) -> QPixmap:
        pm = self.cache.get(id(p))
        if pm is None:
            pm = QPixmap()
            pm.loadFromData(p.thumb)
            self.cache[id(p)] = pm
        return pm

    def paint(self, painter, option, index):
        p: Photo = index.data(Qt.UserRole)
        r = QRectF(option.rect).adjusted(6, 6, -6, -6)
        painter.save()
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        path = QPainterPath()
        path.addRoundedRect(r, 14, 14)

        painter.setClipPath(path)
        painter.fillRect(r, QColor(CARD))
        pm = self._pix(p)
        if not pm.isNull():  # "cover" fit
            s = max(r.width() / pm.width(), r.height() / pm.height())
            w, h = pm.width() * s, pm.height() * s
            painter.drawPixmap(QRectF(r.center().x() - w / 2, r.center().y() - h / 2, w, h), pm, QRectF(pm.rect()))
        if self.verdicts and p.analyzed and p.status == "reject":
            painter.fillRect(r, QColor(10, 12, 20, 105))
        painter.setClipping(False)

        selected = bool(option.state & QStyle.State_Selected)
        if selected:
            painter.setPen(QPen(QColor(ACCENT), 3.5))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(r.adjusted(1.5, 1.5, -1.5, -1.5), 13, 13)

        if not (self.verdicts and p.analyzed):  # not culled yet (or still culling): plain thumbnail, no verdict
            painter.restore()
            return

        # status badge
        name, color = _badge_for(p)
        bc = QPointF(r.right() - 22, r.top() + 22)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(ACCENT) if (selected and p.status == "keep") else QColor(color))
        painter.drawEllipse(bc, 14, 14)
        ic = icons.pixmap(name, "#ffffff", 16, 3.0 if name in ("alert", "check", "x") else 2.2)
        painter.drawPixmap(QRect(int(bc.x()) - 8, int(bc.y()) - 8, 16, 16), ic)

        if p.manual:  # manual-override marker
            tag = QRectF(r.left() + 8, r.bottom() - 26, 56, 18)
            painter.setBrush(QColor(14, 16, 24, 210))
            painter.drawRoundedRect(tag, 9, 9)
            painter.setPen(QColor("#c4b5fd"))
            f = painter.font()
            f.setPixelSize(10)
            f.setBold(True)
            painter.setFont(f)
            painter.drawText(tag, Qt.AlignCenter, "MANUAL")
        painter.restore()


# ------------------------------------------------------------------ zoomable preview
def _overlay() -> QFrame:
    f = QFrame()
    f.setObjectName("overlay")
    return f


def _ov_btn(name: str) -> QToolButton:
    b = QToolButton()
    b.setObjectName("ovBtn")
    b.setIcon(icons.icon(name, "#ffffff", 18, 2.2))
    b.setIconSize(QSize(18, 18))
    b.setCursor(Qt.PointingHandCursor)
    return b


class PreviewView(QWidget):
    prev_clicked = Signal()
    next_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setMinimumSize(420, 320)
        self._pix: QPixmap | None = None
        self._zoom = 1.0
        self._off = QPointF(0, 0)
        self._drag: tuple[QPointF, QPointF] | None = None
        self._empty = "Open a folder (or drop one here) to start culling"

        self.pill = QPushButton(self)
        self.pill.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.pill.setIconSize(QSize(20, 20))

        self.nav = _overlay()
        self.nav.setParent(self)
        nl = QHBoxLayout(self.nav)
        nl.setContentsMargins(6, 4, 6, 4)
        b1, b2 = _ov_btn("left"), _ov_btn("right")
        b1.clicked.connect(self.prev_clicked)
        b2.clicked.connect(self.next_clicked)
        self.nav_lbl = QLabel("0 / 0")
        self.nav_lbl.setStyleSheet("font-size:15px;font-weight:600;padding:0 10px;")
        for w in (b1, self.nav_lbl, b2):
            nl.addWidget(w)

        self.zbox = _overlay()
        self.zbox.setParent(self)
        zl = QHBoxLayout(self.zbox)
        zl.setContentsMargins(6, 4, 6, 4)
        zo, zi = _ov_btn("zoom-out"), _ov_btn("zoom-in")
        zo.clicked.connect(lambda: self.set_zoom(self._zoom / 1.25))
        zi.clicked.connect(lambda: self.set_zoom(self._zoom * 1.25))
        self.z_lbl = QLabel("100%")
        self.z_lbl.setMinimumWidth(52)
        self.z_lbl.setAlignment(Qt.AlignCenter)
        self.z_lbl.setStyleSheet("font-size:14px;font-weight:600;")
        for w in (zo, self.z_lbl, zi):
            zl.addWidget(w)

        self.info = _overlay()
        self.info.setParent(self)
        il = QHBoxLayout(self.info)
        il.setContentsMargins(14, 7, 14, 7)
        self.info_lbl = QLabel("")
        self.info_lbl.setStyleSheet("font-size:13px;")
        il.addWidget(self.info_lbl)

        for w in (self.pill, self.nav, self.zbox, self.info):
            w.hide()

    # --- content
    def set_empty_text(self, t: str):
        self._empty = t
        self.update()

    def set_pixmap(self, pm: QPixmap | None):
        self._pix = pm
        self._zoom, self._off = 1.0, QPointF(0, 0)
        self.z_lbl.setText("100%")
        self.update()

    def show_overlays(self, on: bool, status: bool = True):
        for w in (self.nav, self.zbox, self.info):
            w.setVisible(on)
        self.pill.setVisible(on and status)
        self._layout_overlays()

    def set_status(self, status: str, manual: bool, dup: bool):
        if status == "keep":
            text, col, ic = "Keep", GREEN, "check"
        elif dup:
            text, col, ic = "Duplicate", "#9ca3af", "copy"
        else:
            text, col, ic = "Reject", RED, "x"
        self.pill.setText(f"  {text}" + ("  · manual" if manual else ""))
        self.pill.setIcon(icons.icon(ic, col, 20, 3.0))
        self.pill.setStyleSheet(
            f"QPushButton{{background:rgba(14,16,24,215);color:#fff;border:1.5px solid {col};"
            f"border-radius:18px;padding:8px 20px 8px 14px;font-size:17px;font-weight:700;}}")
        self.pill.adjustSize()

    def set_nav(self, i: int, n: int):
        self.nav_lbl.setText(f"{_fmt(i)} / {_fmt(n)}")
        self.nav.adjustSize()

    def set_info(self, text: str):
        self.info_lbl.setText(text)
        self.info.adjustSize()
        self._layout_overlays()

    # --- zoom / pan
    def set_zoom(self, z: float):
        self._zoom = min(6.0, max(1.0, z))
        if self._zoom == 1.0:
            self._off = QPointF(0, 0)
        self.z_lbl.setText(f"{int(round(self._zoom * 100))}%")
        self.update()

    def wheelEvent(self, e):
        self.set_zoom(self._zoom * (1.15 ** (e.angleDelta().y() / 120)))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self._zoom > 1:
            self._drag = (e.position(), QPointF(self._off))
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._drag:
            start, off0 = self._drag
            self._off = off0 + (e.position() - start)
            self.update()

    def mouseReleaseEvent(self, e):
        self._drag = None
        self.unsetCursor()

    def mouseDoubleClickEvent(self, e):
        self.set_zoom(1.0 if self._zoom > 1 else 2.0)

    # --- painting / layout
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 16, 16)
        p.setClipPath(path)
        p.fillRect(self.rect(), QColor("#0a0c13"))
        if self._pix is None or self._pix.isNull():
            ic = icons.pixmap("image", MUTED, 56, 1.4)
            p.drawPixmap(self.width() // 2 - 28, self.height() // 2 - 64, ic)
            p.setPen(QColor(MUTED))
            f = p.font()
            f.setPixelSize(15)
            p.setFont(f)
            p.drawText(QRect(0, self.height() // 2 + 6, self.width(), 30), Qt.AlignHCenter | Qt.AlignTop, self._empty)
            return
        pw, ph = self._pix.width(), self._pix.height()
        s = min(self.width() / pw, self.height() / ph) * self._zoom
        w, h = pw * s, ph * s
        mx, my = max(0.0, (w - self.width()) / 2), max(0.0, (h - self.height()) / 2)
        self._off = QPointF(min(mx, max(-mx, self._off.x())), min(my, max(-my, self._off.y())))
        x = (self.width() - w) / 2 + self._off.x()
        y = (self.height() - h) / 2 + self._off.y()
        p.drawPixmap(QRectF(x, y, w, h), self._pix, QRectF(self._pix.rect()))

    def _layout_overlays(self):
        W, H, m = self.width(), self.height(), 16
        self.pill.move(m, m)
        self.nav.adjustSize()
        self.nav.move(W - self.nav.width() - m, m)
        self.zbox.adjustSize()
        self.zbox.move(W - self.zbox.width() - m, H - self.zbox.height() - m)
        self.info.setMaximumWidth(max(120, W - self.zbox.width() - 3 * m))
        self.info.adjustSize()
        self.info.move(m, H - self.info.height() - m)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._layout_overlays()


# ------------------------------------------------------------------ main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        from ._version import __version__
        self.setWindowTitle(f"i-arrange  v{__version__}" if __version__ != "dev" else "i-arrange  (dev)")
        self.setWindowIcon(QIcon_from(icons.logo(64)))
        self.resize(1440, 860)
        self.setMinimumSize(1280, 680)
        self.setAcceptDrops(True)
        self.folder: Path | None = None
        self.photos: list[Photo] = []
        self.worker: PoolWorker | None = None
        self._dirty = False  # unsaved culling decisions

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---------- header
        header = QFrame()
        header.setObjectName("header")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 14, 20, 14)
        hl.setSpacing(18)
        logo = QLabel()
        logo.setPixmap(icons.logo(46))
        tb = QVBoxLayout()
        tb.setSpacing(0)
        t = QLabel("i-arrange")
        t.setObjectName("appTitle")
        s = QLabel("Pick the best. Keep it simple.")
        s.setObjectName("muted")
        tb.addWidget(t)
        tb.addWidget(s)
        hl.addWidget(logo)
        hl.addLayout(tb)
        hl.addStretch(1)

        self.btn_open = QPushButton("  Open Folder")
        self.btn_open.setObjectName("openBtn")
        self.btn_open.setIcon(icons.icon("folder", "#c4b5fd", 22, 1.8))
        self.btn_open.setIconSize(QSize(22, 22))
        self.btn_open.setCursor(Qt.PointingHandCursor)
        self.btn_open.clicked.connect(self.open_folder)
        hl.addWidget(self.btn_open)

        self.btn_start = QPushButton("  Start Culling")
        self.btn_start.setObjectName("startBtn")
        self.btn_start.setIcon(icons.icon("play", "#ffffff", 20, 2.2))
        self.btn_start.setIconSize(QSize(20, 20))
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.setMinimumWidth(185)
        self.btn_start.clicked.connect(self.start_culling)
        self.btn_cancel = QPushButton("  Cancel")
        self.btn_cancel.setObjectName("cancelBtn")
        self.btn_cancel.setIcon(icons.icon("x", RED, 20, 2.6))
        self.btn_cancel.setIconSize(QSize(20, 20))
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setMinimumWidth(185)
        self.btn_cancel.clicked.connect(self.cancel_culling)
        hl.addWidget(self.btn_start)
        hl.addWidget(self.btn_cancel)

        self.stats = QLabel("No folder\nJPEG / ARW")
        self.stats.setObjectName("muted")
        hl.addWidget(self.stats)
        hl.addWidget(self._divider())

        self.strict_lbl = QLabel("Strictness:")
        self.strict_lbl.setObjectName("strictLbl")
        self.strict_val = QLabel("50%")
        self.strict_val.setObjectName("strictVal")
        self.strict = QSlider(Qt.Horizontal)
        self.strict.setRange(0, 100)
        self.strict.setValue(50)
        self.strict.setFixedWidth(230)
        self.strict.valueChanged.connect(self.on_strictness)
        ends = QHBoxLayout()
        a, b = QLabel("Lenient"), QLabel("Strict")
        a.setObjectName("muted")
        b.setObjectName("muted")
        ends.addWidget(a)
        ends.addStretch(1)
        ends.addWidget(b)
        sv = QVBoxLayout()
        sv.setSpacing(2)
        sv.addWidget(self.strict)
        sv.addLayout(ends)
        hl.addWidget(self.strict_lbl)
        hl.addWidget(self.strict_val)
        hl.addLayout(sv)
        hl.addStretch(1)

        self.btn_info = QToolButton()
        self.btn_info.setObjectName("iconBtn")
        self.btn_info.setIcon(icons.icon("info", MUTED, 22, 1.8))
        self.btn_info.setIconSize(QSize(22, 22))
        self.btn_info.setCursor(Qt.PointingHandCursor)
        self.btn_info.clicked.connect(self.show_help)
        hl.addWidget(self.btn_info)
        outer.addWidget(header)

        self.progress = QProgressBar()
        self.progress.setObjectName("thin")
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        outer.addWidget(self.progress)

        # ---------- body
        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(14, 12, 14, 12)
        split = QSplitter()
        split.setChildrenCollapsible(False)

        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(10)
        pills = QHBoxLayout()
        pills.setSpacing(8)
        self.tabs = QButtonGroup(self)
        self.tab_btns: dict[str, QPushButton] = {}
        for key, label, ic, col in (("all", "All", "image", "#a5b4fc"), ("keep", "Keep", "check", GREEN),
                                    ("reject", "Reject", "x", RED), ("dup", "Dupes", "copy", "#9ca3af")):
            btn = QPushButton(f" {label} (0)")
            btn.setObjectName("pill")
            btn.setCheckable(True)
            btn.setIcon(icons.icon(ic, col, 18, 2.4))
            btn.setIconSize(QSize(18, 18))
            btn.setCursor(Qt.PointingHandCursor)
            self.tabs.addButton(btn)
            self.tab_btns[key] = btn
            pills.addWidget(btn)
        self.tab_btns["all"].setChecked(True)
        self.tabs.buttonClicked.connect(lambda _b: self.refresh_list())
        pills.addStretch(1)
        ll.addLayout(pills)

        self.delegate = ThumbDelegate(self)
        self.list = QListWidget()
        self.list.setViewMode(QListView.IconMode)
        self.list.setResizeMode(QListView.Adjust)
        self.list.setMovement(QListView.Static)
        self.list.setSpacing(0)
        self.list.setUniformItemSizes(True)
        self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QListWidget.SingleSelection)
        self.list.setItemDelegate(self.delegate)
        self.list.currentItemChanged.connect(self.on_select)
        ll.addWidget(self.list, 1)
        left.setMinimumWidth(420)

        self.preview = PreviewView()
        self.preview.prev_clicked.connect(lambda: self.go(-1))
        self.preview.next_clicked.connect(lambda: self.go(1))
        split.addWidget(left)
        split.addWidget(self.preview)
        split.setStretchFactor(0, 4)
        split.setStretchFactor(1, 7)
        split.setSizes([560, 840])
        bl.addWidget(split)
        outer.addWidget(body, 1)

        # ---------- footer
        footer = QFrame()
        footer.setObjectName("footer")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 6, 24, 6)
        fl.setSpacing(14)
        sh = QLabel()
        sh.setPixmap(icons.pixmap("shield", GREEN, 26, 1.7))
        st = QVBoxLayout()
        st.setSpacing(0)
        l1 = QLabel("Your originals are safe")
        l1.setStyleSheet("font-weight:600;font-size:13px;")
        l2 = QLabel("Your photos are never changed")
        l2.setObjectName("muted")
        st.addWidget(l1)
        st.addWidget(l2)
        fl.addWidget(sh)
        fl.addLayout(st)
        fl.addSpacing(10)
        fl.addWidget(self._divider())
        fl.addSpacing(10)
        fi = QLabel()
        fi.setPixmap(icons.pixmap("folder", "#a5b4fc", 22, 1.7))
        self.counts = QLabel("")
        self.counts.setStyleSheet("font-size:14px;")
        self.counts.setMinimumWidth(230)
        fl.addWidget(fi)
        fl.addWidget(self.counts)
        fl.addStretch(1)

        self.btn_keep = self._action("Keep (K)", "keepBtn", "check", GREEN)
        self.btn_rej = self._action("Reject (X)", "rejectBtn", "x", RED)
        self.btn_dup = self._action("Duplicate (D)", "dupBtn", "copy", "#cfd3e6")
        self.btn_save = self._action("Save", "saveBtn", "save", "#cfd3e6")
        self.btn_save.setToolTip("Save decisions next to the photos so you can reopen them later  (Ctrl+S)")
        self.btn_export = self._action("Export", "exportBtn", "download", "#ffffff")
        self.btn_keep.clicked.connect(lambda: self.set_manual("keep"))
        self.btn_rej.clicked.connect(lambda: self.set_manual("reject"))
        self.btn_dup.clicked.connect(lambda: self.set_manual("reject", "duplicate"))
        self.btn_save.clicked.connect(self.save_session)
        self.btn_export.clicked.connect(self.export)
        for b in (self.btn_keep, self.btn_rej, self.btn_dup):
            fl.addWidget(b)
        fl.addSpacing(8)
        fl.addWidget(self.btn_save)
        fl.addWidget(self.btn_export)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_session)
        outer.addWidget(footer)

        for key, fn in (("K", lambda: self.set_manual("keep")), ("X", lambda: self.set_manual("reject")),
                        ("D", lambda: self.set_manual("reject", "duplicate")), ("A", lambda: self.set_manual(None))):
            QShortcut(QKeySequence(key), self, activated=fn)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(120)
        self._debounce.timeout.connect(self._apply_strictness)

        self.state = "idle"
        self.set_state("idle")

    # ------------------------------------------------------------------ workflow state
    # idle -> loading -> loaded -> analyzing -> results
    def set_state(self, state: str):
        self.state = state
        busy = state in ("loading", "analyzing")
        results = state == "results"
        self.btn_open.setEnabled(not busy)
        self.btn_start.setVisible(state != "analyzing")
        self.btn_cancel.setVisible(state == "analyzing")
        self.btn_start.setEnabled(state == "loaded")
        self.btn_start.setText("  Culling Complete" if results else "  Start Culling")
        self.delegate.verdicts = results
        self.list.viewport().update()
        self.strict.setEnabled(results)
        self.strict_lbl.setEnabled(results)
        self.strict_val.setEnabled(results)
        self._set_actions_enabled(results)
        for key in ("keep", "reject", "dup"):
            self.tab_btns[key].setEnabled(results)
        if not results:
            self.tab_btns["all"].setChecked(True)
        if state == "idle":
            self.counts.setText(f"<span style='color:{MUTED}'>Step 1: open a folder of photos</span>")
        self.update_summary()

    # ------------------------------------------------------------------ small helpers
    def _divider(self) -> QFrame:
        d = QFrame()
        d.setObjectName("divider")
        d.setFixedHeight(38)
        return d

    def _action(self, text: str, name: str, ic: str, col: str) -> QPushButton:
        b = QPushButton(f"  {text}")
        b.setObjectName(name)
        b.setIcon(icons.icon(ic, col, 18, 2.4))
        b.setIconSize(QSize(18, 18))
        b.setCursor(Qt.PointingHandCursor)
        return b

    def _set_actions_enabled(self, on: bool):
        for b in (self.btn_keep, self.btn_rej, self.btn_dup, self.btn_save, self.btn_export):
            b.setEnabled(on)

    def show_help(self):
        QMessageBox.information(
            self, "i-arrange — help",
            "Open a folder of JPEG / ARW photos (or drop one on the window).\n\n"
            "The app flags blurry, badly exposed and duplicate shots. Move the Strictness slider to be more "
            "or less aggressive.\n\n"
            "Keys:\n  K  keep      X  reject      D  mark as duplicate      A  back to automatic\n"
            "  Arrow keys  move between photos\n  Mouse wheel / double-click  zoom the preview\n"
            "  Ctrl+S  save the culling\n\n"
            "Save writes your decisions to a small file next to the photos; reopen the folder later and the app "
            "offers to load it, so nothing has to be analysed again.\n\n"
            "Export copies photos into keep/ and reject/ folders. Originals are never changed.")

    # ------------------------------------------------------------------ loading
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and Path(e.mimeData().urls()[0].toLocalFile()).is_dir():
            e.acceptProposedAction()

    def dropEvent(self, e):
        self.load_folder(Path(e.mimeData().urls()[0].toLocalFile()))

    def open_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Select photo folder", str(self.folder or ""))
        if d:
            self.load_folder(Path(d))

    # Step 1 — load: read every photo and build thumbnails, showing a live count.
    def load_folder(self, folder: Path):
        if self.state in ("loading", "analyzing") or not self._confirm_unsaved():
            return
        items = analysis.discover(folder)
        if not items:
            QMessageBox.information(self, "No photos", "No .jpg / .jpeg / .arw files found in that folder.")
            return
        self.folder = folder
        self.photos = []
        self.delegate.cache.clear()
        self.list.clear()
        self.preview.set_pixmap(None)
        self.preview.show_overlays(False)
        self.preview.set_empty_text(f"Loading {_fmt(len(items))} photos…")
        exts = sorted({Path(f).suffix.lower().lstrip(".") for _, fs in items for f in fs})
        self._kinds = " / ".join("JPEG" if e in ("jpg", "jpeg") else e.upper() for e in exts)
        self.stats.setText(f"{_fmt(len(items))} Photos\n{self._kinds}")
        self.set_state("loading")
        self.progress.setRange(0, len(items))
        self.progress.setValue(0)
        self._on_progress(0, len(items))
        self.worker = PoolWorker(analysis.load_photo, items)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self.on_loaded)
        self.worker.start()

    def _on_progress(self, done: int, total: int):
        if self.state not in ("loading", "analyzing"):
            return  # late signal after cancel
        verb = "Loading photos" if self.state == "loading" else "Culling"
        self.progress.setValue(done)
        self.counts.setText(f"{verb}…  <b>{_fmt(done)}</b> / {_fmt(total)}")
        if self.list.count() == 0 or self.state == "loading":
            self.preview.set_empty_text(f"{verb}…  {_fmt(done)} / {_fmt(total)}")

    def on_loaded(self, photos: list[Photo]):
        self.photos = photos
        self._dirty = False
        self.progress.setValue(0)
        self.set_state("loaded")
        self.preview.set_empty_text("Photos loaded. Press “Start Culling” to analyse them.")
        self.refresh_list()
        self._offer_restore()

    # Step 2 — the explicit "Start Culling" button.  Step 3 — analyse with a live count.
    def start_culling(self):
        if self.state != "loaded" or not self.photos:
            return
        for p in self.photos:
            p.analyzed, p.manual, p.manual_reason = False, None, ""
        self._run_analysis(self.photos)

    def _run_analysis(self, todo: list[Photo]):
        """Analyse the given photos in place (all of them, or just the ones a saved session lacks)."""
        self.set_state("analyzing")
        self.progress.setRange(0, len(todo))
        self.progress.setValue(0)
        self._on_progress(0, len(todo))
        self.worker = PoolWorker(analysis.analyze_photo, [(p,) for p in todo])
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self.on_analyzed)
        self.worker.start()

    def cancel_culling(self):
        if self.worker:
            self.worker.cancel()
            self.worker.wait()
        for p in self.photos:
            p.analyzed, p.manual, p.manual_reason = False, None, ""
        self.progress.setValue(0)
        self.set_state("loaded")
        self.preview.set_empty_text("Culling cancelled. Press “Start Culling” to try again.")
        self.refresh_list()

    # Step 4 — show the result.
    def on_analyzed(self, _done: list[Photo]):
        # photos were analysed in place, so self.photos is already complete
        self.progress.setValue(0)
        analysis.decide(self.photos, self.strict.value() / 100)
        self._dirty = True
        self.set_state("results")
        self.preview.set_empty_text("Select a photo")
        self.refresh_list()

    def on_strictness(self, v: int):
        self.strict_val.setText(f"{v}%")
        if self.state == "results":
            self._debounce.start()

    def _apply_strictness(self):
        analysis.decide(self.photos, self.strict.value() / 100, regroup=False)
        self._dirty = True
        self.refresh_list()

    # ------------------------------------------------------------------ save / restore culling
    def _flash(self, msg: str):
        self.counts.setText(f"<span style='color:{GREEN}'>✓ {msg}</span>")
        QTimer.singleShot(2500, self.update_summary)

    def save_session(self) -> bool:
        if self.state != "results" or not self.folder:
            return False
        try:
            path = session.save(self.folder, self.photos, self.strict.value() / 100)
        except OSError as e:
            QMessageBox.warning(self, "Could not save", f"The culling could not be saved:\n{e}")
            return False
        self._dirty = False
        self._flash("Culling saved")
        return True

    def _offer_restore(self):
        data = session.load(self.folder) if self.folder else None
        if not data:
            return
        when, matched, manual = session.summary(self.photos, data)
        if not matched:
            return
        box = QMessageBox(self)
        box.setWindowTitle("Saved culling found")
        box.setText(f"This folder has a culling saved on {when}.")
        box.setInformativeText(f"{matched} photos match, with {manual} manual change{'s' if manual != 1 else ''}.\n\n"
                               "Load it, or start fresh? (Starting fresh leaves the saved file alone until you save.)")
        load_btn = box.addButton("Load saved culling", QMessageBox.AcceptRole)
        box.addButton("Start fresh", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is load_btn:
            self._restore(data)

    def _restore(self, data: dict):
        self.strict.blockSignals(True)
        self.strict.setValue(int(round(float(data.get("strictness", 0.5)) * 100)))
        self.strict.blockSignals(False)
        self.strict_val.setText(f"{self.strict.value()}%")
        missing = session.apply(self.photos, data)
        if missing:  # photos added since the save: analyse just those
            self._run_analysis(missing)
            return
        analysis.decide(self.photos, self.strict.value() / 100)
        self._dirty = False
        self.set_state("results")
        self.preview.set_empty_text("Select a photo")
        self.refresh_list()
        self._flash("Culling loaded")

    def _confirm_unsaved(self) -> bool:
        """True if it is fine to discard the current culling (nothing unsaved, or the user chose to)."""
        if self.state != "results" or not self._dirty:
            return True
        r = QMessageBox.question(self, "Unsaved culling", "You have unsaved culling decisions.",
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
        if r == QMessageBox.Save:
            return self.save_session()
        return r == QMessageBox.Discard

    def closeEvent(self, e):
        if self._confirm_unsaved():
            e.accept()
        else:
            e.ignore()

    # ------------------------------------------------------------------ list
    def _filter_key(self) -> str:
        for k, b in self.tab_btns.items():
            if b.isChecked():
                return k
        return "all"

    @staticmethod
    def _is_dup(p: Photo) -> bool:
        """Rejected as a duplicate, automatically or by the user (D key)."""
        if p.status != "reject":
            return False
        return p.manual_reason == "duplicate" if p.manual else "duplicate" in p.reason

    def _visible(self, p: Photo) -> bool:
        """A photo belongs to a tab only while its current status matches it."""
        k = self._filter_key()
        if k == "keep":
            return p.status == "keep"
        if k == "reject":
            return p.status == "reject"
        if k == "dup":
            return self._is_dup(p)
        return True

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._relayout_grid()

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self._relayout_grid)

    def _relayout_grid(self):
        vw = self.list.width() - 22  # reserve room for the scrollbar so columns don't re-wrap when it appears
        if vw <= 0:
            return
        cols = max(2, round(vw / 190))
        cw = vw // cols
        self.delegate.cell = QSize(cw, int(cw * 1.22))
        self.list.setGridSize(self.delegate.cell)
        self.list.doItemsLayout()

    def refresh_list(self):
        cur = self.current_photo()
        self.list.blockSignals(True)
        self.list.setUpdatesEnabled(False)
        self.list.clear()
        row = 0
        for p in self.photos:
            if not self._visible(p):
                continue
            it = QListWidgetItem()
            it.setData(Qt.UserRole, p)
            it.setSizeHint(self.delegate.cell)
            self.list.addItem(it)
            if cur is p:
                row = self.list.count() - 1
        self.list.setUpdatesEnabled(True)
        self.list.blockSignals(False)
        self._relayout_grid()
        # right after loading, show the hint instead of auto-selecting a photo
        if self.list.count() and (cur is not None or self.state == "results"):
            self.list.setCurrentRow(row)
            self.on_select(self.list.currentItem(), None)
        else:
            self.list.setCurrentRow(-1)
            self.preview.set_pixmap(None)
            if self.state == "results" and not self.list.count():
                self.preview.set_empty_text("No photos in this filter")
            self.preview.show_overlays(False)
        self.update_summary()

    def update_summary(self):
        n = len(self.photos)
        results = self.state == "results"
        if results:
            k = sum(1 for p in self.photos if p.status == "keep")
            d = sum(1 for p in self.photos if self._is_dup(p))
            counts = (("all", "All", n), ("keep", "Keep", k), ("reject", "Reject", n - k), ("dup", "Dupes", d))
            self.counts.setText(f"<b>{_fmt(k)}</b> Keepers &nbsp;•&nbsp; <b>{_fmt(n - k)}</b> Rejects")
        else:
            counts = (("all", "All", n), ("keep", "Keep", None), ("reject", "Reject", None), ("dup", "Dupes", None))
            if self.state == "loaded":
                self.counts.setText(f"<b>{_fmt(n)}</b> photos loaded &nbsp;•&nbsp; "
                                    f"<span style='color:{MUTED}'>Step 2: press Start Culling</span>")
        for key, label, cnt in counts:
            self.tab_btns[key].setText(f" {label} ({'–' if cnt is None else _fmt(cnt)})")

    def current_photo(self) -> Photo | None:
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it else None

    def go(self, delta: int):
        r = self.list.currentRow() + delta
        if 0 <= r < self.list.count():
            self.list.setCurrentRow(r)

    def on_select(self, item, _prev):
        p: Photo | None = item.data(Qt.UserRole) if item else None
        if not p:
            return
        try:
            img = analysis.load_preview(p.path, 2400)
            qi = QImage(img.tobytes(), img.width, img.height, img.width * 3, QImage.Format_RGB888).copy()
            self.preview.set_pixmap(QPixmap.fromImage(qi))
        except Exception as ex:
            self.preview.set_pixmap(None)
            self.preview.set_empty_text(f"Cannot load preview: {ex}")
        self.refresh_selected_info(p)

    def refresh_selected_info(self, p: Photo):
        if not p.analyzed:  # loaded but not culled yet
            self.preview.set_nav(self.list.currentRow() + 1, self.list.count())
            self.preview.set_info(f"<b>{p.name}</b> &nbsp;·&nbsp; Not culled yet")
            self.preview.show_overlays(True, status=False)
            return
        dup = self._is_dup(p)
        self.preview.set_status(p.status, bool(p.manual), dup)
        self.preview.set_nav(self.list.currentRow() + 1, self.list.count())
        reason = ("Marked by you" + (" as duplicate" if p.manual_reason else "")) if p.manual \
            else p.reason[:1].upper() + p.reason[1:]
        parts = [f"<b>{p.name}</b>", reason, f"Score {p.score:.0f}", f"Sharpness {p.sharp_norm:.2f}"]
        if p.n_faces:
            parts.append(f"{p.n_faces} face{'s' if p.n_faces != 1 else ''}")
        if p.eyes_hint:
            parts.append("eyes may be closed (hint)")
        if p.group_size > 1:
            parts.append(f"Group {p.group + 1}: #{p.group_rank + 1} of {p.group_size}")
        self.preview.set_info(" &nbsp;·&nbsp; ".join(parts))
        self.preview.show_overlays(True)

    # ------------------------------------------------------------------ actions
    def set_manual(self, status: str | None, reason: str = ""):
        p = self.current_photo()
        if not p or not p.analyzed or self.state != "results":
            return
        p.manual = status
        p.manual_reason = reason if status else ""
        self._dirty = True
        self.update_summary()
        if not self._visible(p):
            # it no longer belongs to the active filter (e.g. rejected while viewing Keep): drop it from the
            # list and show whatever slid into its place
            row = self.list.currentRow()
            self.list.blockSignals(True)
            self.list.takeItem(row)
            if self.list.count():
                self.list.setCurrentRow(min(row, self.list.count() - 1))
            self.list.blockSignals(False)
            if self.list.count():
                self.on_select(self.list.currentItem(), None)
            else:
                self.preview.set_pixmap(None)
                self.preview.set_empty_text("No photos in this filter")
                self.preview.show_overlays(False)
            self.list.viewport().update()
            return
        self.list.viewport().update()
        self.refresh_selected_info(p)
        if status:  # auto-advance after a decision
            self.go(1)

    def export(self):
        if not self.photos:
            return
        default = str(self.folder / "culled") if self.folder else ""
        dest = QFileDialog.getExistingDirectory(self, "Export folder (keep/ and reject/ subfolders are created)", default)
        if not dest:
            return
        dest_p = Path(dest)
        jobs = [(f, dest_p / p.status / Path(f).name) for p in self.photos for f in p.files]
        dlg = QProgressDialog("Copying files…", "Cancel", 0, len(jobs), self)
        dlg.setWindowModality(Qt.WindowModal)
        copied = 0
        for i, (src, dst) in enumerate(jobs):
            if dlg.wasCanceled():
                break
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
            dlg.setValue(i + 1)
            QApplication.processEvents()
        QMessageBox.information(self, "Export",
                                f"Copied {copied} of {len(jobs)} files to\n{dest_p}\n\nOriginals were not touched.")


def QIcon_from(pm: QPixmap):
    from PySide6.QtGui import QIcon
    return QIcon(pm)


def run():
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    try:
        app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    except Exception:
        pass
    app.setStyleSheet(QSS)
    w = MainWindow()
    w.show()
    app.exec()
