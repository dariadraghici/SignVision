from PySide6.QtCore import QByteArray, Qt, QPointF
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer


_SCAN_CAMERA_SVG = """<svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M6 14V8a2 2 0 0 1 2 -2h6" stroke="{c}" stroke-width="2.2" stroke-linecap="round"/>
  <path d="M42 14V8a2 2 0 0 0 -2 -2h-6" stroke="{c}" stroke-width="2.2" stroke-linecap="round"/>
  <path d="M6 34v6a2 2 0 0 0 2 2h6" stroke="{c}" stroke-width="2.2" stroke-linecap="round"/>
  <path d="M42 34v6a2 2 0 0 1 -2 2h-6" stroke="{c}" stroke-width="2.2" stroke-linecap="round"/>
  <circle cx="24" cy="24" r="7" stroke="{c}" stroke-width="2.2"/>
  <circle cx="24" cy="24" r="2.4" fill="{c}"/>
</svg>"""

_WEBCAM_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="12" cy="9" r="6" stroke="{c}" stroke-width="1.6"/>
  <circle cx="12" cy="9" r="2.1" fill="{c}"/>
  <path d="M8 20h8M12 15v5" stroke="{c}" stroke-width="1.6" stroke-linecap="round"/>
</svg>"""

_UPLOAD_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M4 7a2 2 0 0 1 2 -2h3l2 2h7a2 2 0 0 1 2 2v8a2 2 0 0 1 -2 2H6a2 2 0 0 1 -2 -2z" stroke="{c}" stroke-width="1.6" stroke-linejoin="round"/>
  <path d="M12 17v-5.2M9.4 14.4L12 11.8l2.6 2.6" stroke="{c}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""

_CLAPPER_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M3 9.5L4.6 5h15L21 9.5H3z" stroke="{c}" stroke-width="1.3" stroke-linejoin="round"/>
  <rect x="3" y="9.5" width="18" height="10" rx="1.5" stroke="{c}" stroke-width="1.3"/>
  <path d="M7.2 5l2 4.5M12 5l2 4.5M16.8 5l2 4.5" stroke="{c}" stroke-width="1.3"/>
</svg>"""

_CHAT_BUBBLE_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M4 5h16v10H9l-4 4v-4H4z" stroke="{c}" stroke-width="1.5" stroke-linejoin="round"/>
  <circle cx="8.5" cy="10" r="0.9" fill="{c}"/>
  <circle cx="12" cy="10" r="0.9" fill="{c}"/>
  <circle cx="15.5" cy="10" r="0.9" fill="{c}"/>
</svg>"""

_LIGHTNING_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M13 3L5 14h5l-1 7 8-11h-5z" stroke="{c}" stroke-width="1.4" stroke-linejoin="round" stroke-linecap="round"/>
</svg>"""

_TARGET_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <circle cx="12" cy="12" r="8" stroke="{c}" stroke-width="1.4"/>
  <circle cx="12" cy="12" r="3.2" stroke="{c}" stroke-width="1.4"/>
  <path d="M12 2v3M12 19v3M2 12h3M19 12h3" stroke="{c}" stroke-width="1.4" stroke-linecap="round"/>
</svg>"""

_FILE_PLAY_SVG = """<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M6 3h7l5 5v13a1 1 0 0 1 -1 1H6a1 1 0 0 1 -1 -1V4a1 1 0 0 1 1 -1z" stroke="{c}" stroke-width="1.4" stroke-linejoin="round"/>
  <path d="M13 3v5h5" stroke="{c}" stroke-width="1.4" stroke-linejoin="round"/>
  <circle cx="9" cy="16.5" r="3.4" stroke="{c}" stroke-width="1.3"/>
  <path d="M8 15l2.4 1.5L8 18z" fill="{c}"/>
</svg>"""

_TEMPLATES = {
    "scan_camera": _SCAN_CAMERA_SVG,
    "webcam": _WEBCAM_SVG,
    "upload": _UPLOAD_SVG,
    "clapper": _CLAPPER_SVG,
    "chat_bubble": _CHAT_BUBBLE_SVG,
    "lightning": _LIGHTNING_SVG,
    "target": _TARGET_SVG,
    "file_play": _FILE_PLAY_SVG,
}

_LOGO_SVG = """<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#2dd4bf"/>
      <stop offset="100%" stop-color="#a855f7"/>
    </linearGradient>
  </defs>
  <path d="M20 32V22a4 4 0 0 1 4 -4h10" stroke="url(#grad1)" stroke-width="3" stroke-linecap="round" fill="none"/>
  <path d="M80 32V22a4 4 0 0 0 -4 -4H66" stroke="url(#grad1)" stroke-width="3" stroke-linecap="round" fill="none"/>
  <path d="M20 68v10a4 4 0 0 0 4 4h10" stroke="url(#grad1)" stroke-width="3" stroke-linecap="round" fill="none"/>
  <path d="M80 68v10a4 4 0 0 1 -4 4H66" stroke="url(#grad1)" stroke-width="3" stroke-linecap="round" fill="none"/>
  <circle cx="50" cy="50" r="26" stroke="url(#grad1)" stroke-width="2.2" fill="none" opacity="0.7"/>
  <g stroke="url(#grad1)" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" fill="none">
    <path d="M40 52V34a3 3 0 0 1 6 0v14"/>
    <path d="M46 48V30a3 3 0 0 1 6 0v18"/>
    <path d="M52 48V33a3 3 0 0 1 6 0v20"/>
    <path d="M58 53V40a3 3 0 0 1 6 0v14a13 13 0 0 1 -13 13h-2a15 15 0 0 1 -13.5 -8.5L33 54a2.8 2.8 0 0 1 4.6 -3.2L40 54"/>
  </g>
</svg>"""


def make_icon_pixmap(name: str, color: str, size: int, device_ratio: float = 2.0) -> QPixmap:
    svg = _TEMPLATES[name].format(c=color)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))

    px_size = max(1, int(size * device_ratio))
    pixmap = QPixmap(px_size, px_size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()

    pixmap.setDevicePixelRatio(device_ratio)
    return pixmap


def make_logo_pixmap(size: int, device_ratio: float = 2.0) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(_LOGO_SVG.encode("utf-8")))

    px_size = max(1, int(size * device_ratio))
    pixmap = QPixmap(px_size, px_size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter)
    painter.end()

    pixmap.setDevicePixelRatio(device_ratio)
    return pixmap


def hex_to_rgb(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"{r}, {g}, {b}"
