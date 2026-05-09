"""
EMAG Player - SVG Icons
모든 버튼 아이콘을 SVG로 직접 렌더링
"""

from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import QByteArray


def _render_svg(svg: str, size: int, color: str) -> QPixmap:
    """SVG 문자열 → QPixmap"""
    svg_bytes = svg.replace("{{color}}", color).encode("utf-8")
    renderer = QSvgRenderer(QByteArray(svg_bytes))
    px = QPixmap(QSize(size, size))
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(p)
    p.end()
    return px


# ── SVG 정의 ──────────────────────────────────

_PLAY = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <polygon points="6,3 21,12 6,21" fill="{{color}}"/>
</svg>"""

_PAUSE = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <rect x="4" y="3" width="5" height="18" rx="1.5" fill="{{color}}"/>
  <rect x="15" y="3" width="5" height="18" rx="1.5" fill="{{color}}"/>
</svg>"""

_STOP = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <rect x="4" y="4" width="16" height="16" rx="2" fill="{{color}}"/>
</svg>"""

_SKIP_NEXT = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <polygon points="4,3 17,12 4,21" fill="{{color}}"/>
  <rect x="18" y="3" width="3" height="18" rx="1.5" fill="{{color}}"/>
</svg>"""

_SKIP_PREV = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <polygon points="20,3 7,12 20,21" fill="{{color}}"/>
  <rect x="3" y="3" width="3" height="18" rx="1.5" fill="{{color}}"/>
</svg>"""

_SHUFFLE = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M2 5h4l12 14h4" stroke="{{color}}" stroke-width="2.2" stroke-linecap="round" fill="none"/>
  <path d="M2 19h4L18 5h4" stroke="{{color}}" stroke-width="2.2" stroke-linecap="round" fill="none"/>
  <polyline points="18,2 22,5 18,8" stroke="{{color}}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <polyline points="18,16 22,19 18,22" stroke="{{color}}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
</svg>"""

_REPEAT = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M17 2l4 4-4 4" stroke="{{color}}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <path d="M3 11V9a4 4 0 014-4h14" stroke="{{color}}" stroke-width="2.2" stroke-linecap="round" fill="none"/>
  <path d="M7 22l-4-4 4-4" stroke="{{color}}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <path d="M21 13v2a4 4 0 01-4 4H3" stroke="{{color}}" stroke-width="2.2" stroke-linecap="round" fill="none"/>
</svg>"""

_REPEAT_ONE = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M17 2l4 4-4 4" stroke="{{color}}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <path d="M3 11V9a4 4 0 014-4h14" stroke="{{color}}" stroke-width="2.2" stroke-linecap="round" fill="none"/>
  <path d="M7 22l-4-4 4-4" stroke="{{color}}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <path d="M21 13v2a4 4 0 01-4 4H3" stroke="{{color}}" stroke-width="2.2" stroke-linecap="round" fill="none"/>
  <text x="12" y="14" text-anchor="middle" font-size="7" font-weight="bold" fill="{{color}}">1</text>
</svg>"""

_VOLUME = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <polygon points="3,9 7,9 12,4 12,20 7,15 3,15" fill="{{color}}"/>
  <path d="M16 8a6 6 0 010 8" stroke="{{color}}" stroke-width="2" stroke-linecap="round" fill="none"/>
  <path d="M19 5a10 10 0 010 14" stroke="{{color}}" stroke-width="2" stroke-linecap="round" fill="none"/>
</svg>"""

_FOLDER = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"
        fill="{{color}}" opacity="0.9"/>
  <path d="M3 9h18" stroke="white" stroke-width="1" opacity="0.3"/>
</svg>"""

_SEARCH = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <circle cx="10.5" cy="10.5" r="6.5" stroke="{{color}}" stroke-width="2.2" fill="none"/>
  <line x1="15.5" y1="15.5" x2="21" y2="21" stroke="{{color}}" stroke-width="2.5" stroke-linecap="round"/>
</svg>"""

_WIDGET = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <rect x="2" y="6" width="20" height="13" rx="3" stroke="{{color}}" stroke-width="2" fill="none"/>
  <circle cx="7" cy="12.5" r="3" fill="{{color}}"/>
  <line x1="12" y1="10" x2="20" y2="10" stroke="{{color}}" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="12" y1="13" x2="18" y2="13" stroke="{{color}}" stroke-width="1.8" stroke-linecap="round"/>
  <line x1="12" y1="16" x2="16" y2="16" stroke="{{color}}" stroke-width="1.8" stroke-linecap="round"/>
</svg>"""

_PALETTE = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M12 2C6.48 2 2 6.48 2 12c0 5.52 4.48 10 10 10 1.1 0 2-.9 2-2 0-.56-.22-1.05-.58-1.41-.35-.37-.58-.87-.58-1.41 0-1.1.9-2 2-2h2.36c3.1 0 5.8-2.52 5.8-5.6C23 6.04 18.03 2 12 2z"
        fill="{{color}}" opacity="0.85"/>
  <circle cx="7" cy="12" r="1.5" fill="white"/>
  <circle cx="9.5" cy="7.5" r="1.5" fill="white"/>
  <circle cx="14.5" cy="7.5" r="1.5" fill="white"/>
  <circle cx="17" cy="12" r="1.5" fill="white"/>
</svg>"""

_PIN = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M12 2l2 6h5l-4 3 1.5 6L12 14l-4.5 3L9 11 5 8h5z" fill="{{color}}"/>
  <line x1="12" y1="14" x2="12" y2="22" stroke="{{color}}" stroke-width="2" stroke-linecap="round"/>
</svg>"""

# 핀 고정 ON — 압정이 내려꽂힌 모양 (굵고 선명)
_PIN_ON = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M16 3a1 1 0 011 1v1.17a3 3 0 011.83 2.62L19 8v1h1a1 1 0 010 2h-6v6l1 3h-6l1-3v-6H4a1 1 0 010-2h1V8a3 3 0 012-2.83V4a1 1 0 011-1h8z"
        fill="{{color}}"/>
</svg>"""

# 핀 고정 OFF — 빈 압정 윤곽
_PIN_OFF = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M16 3a1 1 0 011 1v1.17a3 3 0 011.83 2.62L19 8v1h1a1 1 0 010 2h-6v6l1 3h-6l1-3v-6H4a1 1 0 010-2h1V8a3 3 0 012-2.83V4a1 1 0 011-1h8z"
        stroke="{{color}}" stroke-width="1.5" fill="none"/>
</svg>"""

_CLOSE = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <line x1="5" y1="5" x2="19" y2="19" stroke="{{color}}" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="19" y1="5" x2="5" y2="19" stroke="{{color}}" stroke-width="2.5" stroke-linecap="round"/>
</svg>"""

_MUSIC_NOTE = """<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
  <path d="M9 18V5l12-2v13" stroke="{{color}}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <circle cx="6" cy="18" r="3" fill="{{color}}"/>
  <circle cx="18" cy="16" r="3" fill="{{color}}"/>
</svg>"""


# ── 공개 API ──────────────────────────────────

def icon(name: str, color: str, size: int = 20) -> QPixmap:
    """아이콘 이름 → QPixmap"""
    _MAP = {
        "play":        _PLAY,
        "pause":       _PAUSE,
        "stop":        _STOP,
        "next":        _SKIP_NEXT,
        "prev":        _SKIP_PREV,
        "shuffle":     _SHUFFLE,
        "repeat":      _REPEAT,
        "repeat_one":  _REPEAT_ONE,
        "volume":      _VOLUME,
        "folder":      _FOLDER,
        "search":      _SEARCH,
        "widget":      _WIDGET,
        "palette":     _PALETTE,
        "pin":         _PIN,
        "pin_on":      _PIN_ON,
        "pin_off":     _PIN_OFF,
        "close":       _CLOSE,
        "music_note":  _MUSIC_NOTE,
    }
    svg = _MAP.get(name, _MUSIC_NOTE)
    return _render_svg(svg, size, color)


def set_icon(btn, name: str, color: str, size: int = 18):
    """QPushButton에 SVG 아이콘 세팅"""
    from PyQt6.QtGui import QIcon
    px = icon(name, color, size * 2)  # 고해상도 렌더
    btn.setIcon(QIcon(px))
    btn.setIconSize(QSize(size, size))
    btn.setText("")
