"""
EMAG Player - Theme System
컬러 테마 프리셋 + 커스텀 색상 지원
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
import sys
import paths

THEME_FILE: Path = paths.BASE_DIR / "theme.json" 


@dataclass
class Theme:
    name: str
    bg: str          # 배경
    surface: str     # 카드/패널
    surface2: str    # 서브 패널
    border: str      # 경계선
    accent: str      # 주 강조색
    accent2: str     # 보조 강조색
    text: str        # 기본 텍스트
    muted: str       # 흐린 텍스트
    hover: str       # 호버 배경
    header_bg: str   # 헤더 배경
    header_text: str # 헤더 텍스트


PRESETS: dict[str, Theme] = {
    "니나마무": Theme(
        name="니나마무",
        bg="#fdf6ee", surface="#ffffff", surface2="#fff8f0",
        border="#f0d9c0", accent="#f07800", accent2="#f5a830",
        text="#2a1f14", muted="#b09070", hover="#fff0e0",
        header_bg="#f07800", header_text="#ffffff",
    ),
    "미드나잇": Theme(
        name="미드나잇",
        bg="#0d0f14", surface="#161920", surface2="#1a1d25",
        border="#252a38", accent="#7c6ef7", accent2="#a78bfa",
        text="#e2e8f0", muted="#4a5568", hover="#1e2235",
        header_bg="#7c6ef7", header_text="#ffffff",
    ),
    "오션": Theme(
        name="오션",
        bg="#0a1628", surface="#0f2040", surface2="#112240",
        border="#1e3a5f", accent="#00d4aa", accent2="#38bdf8",
        text="#ccd6f6", muted="#4a6080", hover="#162a4a",
        header_bg="#00d4aa", header_text="#0a1628",
    ),
    "로즈": Theme(
        name="로즈",
        bg="#1a0a10", surface="#2a1020", surface2="#2e1525",
        border="#4a2535", accent="#f472b6", accent2="#fb7185",
        text="#fce7f3", muted="#7a3555", hover="#3a1530",
        header_bg="#f472b6", header_text="#1a0a10",
    ),
    "포레스트": Theme(
        name="포레스트",
        bg="#0a140c", surface="#101e12", surface2="#132016",
        border="#1e3520", accent="#4ade80", accent2="#86efac",
        text="#dcfce7", muted="#3a6040", hover="#162518",
        header_bg="#4ade80", header_text="#0a140c",
    ),
    "모노크롬": Theme(
        name="모노크롬",
        bg="#111111", surface="#1c1c1c", surface2="#202020",
        border="#333333", accent="#e5e5e5", accent2="#aaaaaa",
        text="#f5f5f5", muted="#555555", hover="#252525",
        header_bg="#e5e5e5", header_text="#111111",
    ),
    "라이트": Theme(
        name="라이트",
        bg="#f8fafc", surface="#ffffff", surface2="#f1f5f9",
        border="#e2e8f0", accent="#3b82f6", accent2="#60a5fa",
        text="#1e293b", muted="#94a3b8", hover="#eff6ff",
        header_bg="#3b82f6", header_text="#ffffff",
    ),
}


def load_theme() -> Theme:
    """저장된 테마 로드 (없으면 기본값)"""
    if THEME_FILE.exists():
        try:
            data = json.loads(THEME_FILE.read_text(encoding="utf-8"))
            name = data.get("name", "니나마무")
            if name in PRESETS and not data.get("custom"):
                return PRESETS[name]
            # 커스텀 테마
            return Theme(**{k: data[k] for k in Theme.__dataclass_fields__ if k in data})
        except Exception:
            pass
    return PRESETS["니나마무"]


def save_theme(theme: Theme):
    try:
        THEME_FILE.write_text(
            json.dumps(asdict(theme), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception:
        pass


def build_stylesheet(t: Theme) -> str:
    return f"""
QMainWindow {{
    background-color: {t.bg};
}}
QWidget {{
    background-color: transparent;
    color: {t.text};
    font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
    font-size: 13px;
}}
QMainWindow > QWidget {{
    background-color: {t.bg};
}}
QLineEdit {{
    background: {t.surface};
    border: 2px solid {t.border};
    border-radius: 8px;
    padding: 8px 12px;
    color: {t.text};
    font-size: 13px;
    selection-background-color: {t.accent2};
}}
QLineEdit:focus {{ border-color: {t.accent}; }}
QPushButton {{
    background: {t.surface};
    border: 2px solid {t.border};
    border-radius: 8px;
    color: {t.text};
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton:hover {{
    background: {t.hover};
    border-color: {t.accent};
    color: {t.accent};
}}
QPushButton:pressed {{ background: {t.surface2}; border-color: {t.accent}; }}
QPushButton:disabled {{ color: {t.muted}; border-color: {t.border}; background: {t.bg}; }}
QPushButton#accent {{
    background: {t.accent}; border: 2px solid {t.accent};
    color: {t.header_text}; font-weight: 700;
}}
QPushButton#accent:hover {{ background: {t.accent2}; border-color: {t.accent2}; }}
QPushButton#ctrl {{
    background: transparent; border: none;
    color: {t.muted}; font-size: 20px;
    border-radius: 20px; min-width: 38px; min-height: 38px;
}}
QPushButton#ctrl:hover {{ background: {t.hover}; color: {t.accent}; }}
QPushButton#play_btn {{
    background: {t.accent}; border: none;
    color: {t.header_text}; font-size: 20px; font-weight: bold;
    border-radius: 22px;
    min-width: 44px; min-height: 44px;
    max-width: 44px; max-height: 44px;
}}
QPushButton#play_btn:hover {{ background: {t.accent2}; }}
QListWidget {{
    background: {t.surface}; border: 2px solid {t.border};
    border-radius: 8px; outline: none; padding: 2px 0;
}}
QListWidget::item {{
    padding: 7px 12px; border-bottom: 1px solid {t.border}; color: {t.text};
}}
QListWidget::item:hover {{ background: {t.hover}; }}
QListWidget::item:selected {{ background: {t.hover}; color: {t.accent}; }}
QListWidget#search_results {{
    background: {t.surface2}; border: 2px solid {t.border}; border-radius: 8px;
}}
QSlider::groove:horizontal {{
    height: 5px; background: {t.border}; border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: {t.accent}; border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {t.accent}; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px; border: 2px solid {t.bg};
}}
QSlider::handle:horizontal:hover {{
    background: {t.accent2}; width: 16px; height: 16px;
    margin: -6px 0; border-radius: 8px;
}}
QFrame[role="panel"] {{
    background: {t.surface}; border: 2px solid {t.border}; border-radius: 12px;
}}
QFrame[role="divider"] {{
    background: {t.border}; max-height: 2px;
}}
QScrollBar:vertical {{
    background: {t.bg}; width: 5px; border: none;
}}
QScrollBar::handle:vertical {{
    background: {t.border}; border-radius: 3px; min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{ background: {t.accent}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ height: 5px; background: {t.bg}; border: none; }}
QScrollBar::handle:horizontal {{ background: {t.border}; border-radius: 3px; }}
QLabel#title {{ color: {t.text}; font-size: 14px; font-weight: 700; }}
QLabel#subtitle {{ color: {t.muted}; font-size: 11px; }}
QLabel#time {{ color: {t.muted}; font-size: 11px; font-family: 'Consolas', monospace; }}
QLabel#section {{ color: {t.accent}; font-size: 10px; font-weight: 700; letter-spacing: 2px; }}
QMenu {{
    background: {t.surface}; border: 2px solid {t.border};
    border-radius: 8px; padding: 4px;
}}
QMenu::item {{ padding: 7px 16px; border-radius: 5px; }}
QMenu::item:selected {{ background: {t.hover}; color: {t.accent}; }}
QDialog {{
    background: {t.bg};
}}
"""
