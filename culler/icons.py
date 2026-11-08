"""Vector icons (Lucide-style strokes) rendered from inline SVG, plus the app logo."""
from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtSvg import QSvgRenderer

_BODY = {
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "x": '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    "copy": '<rect x="9" y="9" width="13" height="13" rx="2"/>'
            '<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    "alert": '<line x1="12" y1="5" x2="12" y2="14"/><line x1="12" y1="19" x2="12.01" y2="19"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41'
           'M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
    "folder": '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/>',
    "camera": '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>'
              '<circle cx="12" cy="13" r="4"/>',
    "left": '<polyline points="15 18 9 12 15 6"/>',
    "right": '<polyline points="9 18 15 12 9 6"/>',
    "zoom-in": '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>'
               '<line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>',
    "zoom-out": '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>'
                '<line x1="8" y1="11" x2="14" y2="11"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/>'
                '<line x1="12" y1="15" x2="12" y2="3"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/>'
             '<polyline points="21 15 16 10 5 21"/>',
    "save": '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>'
            '<polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
    "play":'<polygon points="6 3 20 12 6 21 6 3"/>',
    "info":'<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/>'
            '<line x1="12" y1="8" x2="12.01" y2="8"/>',
}


@lru_cache(maxsize=None)
def pixmap(name: str, color: str = "#ffffff", size: int = 20, sw: float = 2.0) -> QPixmap:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round">{_BODY[name]}</svg>'
    )
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    QSvgRenderer(QByteArray(svg.encode())).render(p)
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm


def icon(name: str, color: str = "#ffffff", size: int = 20, sw: float = 2.0) -> QIcon:
    return QIcon(pixmap(name, color, size, sw))


def logo(size: int = 44) -> QPixmap:
    """Rounded indigo-violet square with a white camera glyph."""
    dpr = 2
    pm = QPixmap(size * dpr, size * dpr)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(QPointF(0, 0), QPointF(size * dpr, size * dpr))
    g.setColorAt(0, QColor("#6d70ff"))
    g.setColorAt(1, QColor("#8b5cf6"))
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, size * dpr, size * dpr), size * dpr * 0.28, size * dpr * 0.28)
    p.fillPath(path, g)
    glyph = pixmap("camera", "#ffffff", int(size * 0.55), 2.0)
    gs = glyph.width() / glyph.devicePixelRatio()
    p.drawPixmap(QRectF((size * dpr - gs * dpr) / 2, (size * dpr - gs * dpr) / 2, gs * dpr, gs * dpr), glyph,
                 QRectF(glyph.rect()))
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm
