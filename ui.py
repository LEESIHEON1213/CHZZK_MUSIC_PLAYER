"""
니나마무's 플레이어 — Remote Control UI
v6: 즐겨찾기, 큐 표시, seek, 볼륨 재시작, 플레이리스트, 종료 정리
"""

import sys, json, random, threading, urllib.request
from pathlib import Path
from typing import Optional, List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QSlider, QFrame, QSizePolicy, QFileDialog, QMenu, QDialog,
    QGridLayout, QColorDialog,
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QObject, QSize, QPoint,
    QRunnable, QThreadPool, pyqtSlot, QRect,
)
from PyQt6.QtGui import QFont, QColor, QPixmap, QImage, QDragEnterEvent, QDropEvent, QCloseEvent, QPainter, QPen, QFontMetrics

from player import EMAGPlayer, Track, search_youtube, file_to_track, kill_all_ffmpeg, fetch_playlist
from theme import Theme, PRESETS, load_theme, save_theme, build_stylesheet
from widget import StreamWidget
from updater import run_updates_async, check_tools_exist
import icons as IC


APP_NAME = "니나마무's 플레이어 //"


# ─────────────────────────────────────────────
# 마퀴 스크롤 라벨 (오른쪽→왼쪽 흐름)
# ─────────────────────────────────────────────

class MarqueeLabel(QWidget):
    """텍스트가 오른쪽에서 왼쪽으로 부드럽게 흐르는 라벨."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self._color = "#ffffff"
        self._font = QFont("Malgun Gothic", 10, QFont.Weight.Bold)
        # 스크롤 상태: 오른쪽 끝에서 시작해 왼쪽으로 이동
        # _pos: 텍스트 왼쪽 끝의 x 좌표 (width()에서 시작 → 음수까지)
        self._pos = 0.0
        self._text_w = 0
        self._speed = 1.2
        self._gap = 80          # 루프 간격
        self._started = False   # 첫 사이클 시작 여부

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(20)

    def set_style(self, color: str, font_size: int = 10):
        self._color = color
        self._font = QFont("Malgun Gothic", font_size, QFont.Weight.Bold)
        self._calc_text_w()
        self.update()

    def setText(self, text: str):
        self._text = text
        self._calc_text_w()
        self._reset()
        self.update()

    def _calc_text_w(self):
        if self._text:
            fm = QFontMetrics(self._font)
            self._text_w = fm.horizontalAdvance(self._text)

    def _reset(self):
        # 텍스트를 위젯 오른쪽 끝에서 시작
        self._pos = float(self.width()) if self.width() > 0 else 500.0
        self._started = True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 아직 시작 안 했거나 텍스트가 짧아 스크롤 불필요하면 위치 재조정
        if not self._started and self._text:
            self._reset()

    def showEvent(self, event):
        super().showEvent(event)
        if self._text and not self._started:
            QTimer.singleShot(0, self._reset)

    def _need_scroll(self):
        return self._text_w > self.width() if self.width() > 0 else False

    def _tick(self):
        if not self._text:
            return
        # width 확정 전이면 대기
        if self.width() <= 0:
            return
        # 아직 시작 안 했으면 지금 시작
        if not self._started:
            self._reset()
            return
        # 텍스트가 충분히 짧으면 스크롤 불필요
        if not self._need_scroll():
            return
        self._pos -= self._speed
        # 텍스트가 완전히 왼쪽으로 사라지면 오른쪽 끝으로 루프
        if self._pos < -(self._text_w + self._gap):
            self._pos = float(self.width())
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(self._font)
        p.setPen(QColor(self._color))
        w, h = self.width(), self.height()
        fm = QFontMetrics(self._font)
        y = (h + fm.ascent() - fm.descent()) // 2
        p.setClipRect(QRect(0, 0, w, h))
        if self._need_scroll():
            p.drawText(int(self._pos), y, self._text)
        else:
            # 짧은 텍스트는 왼쪽 정렬 정적 표시
            p.drawText(0, y, self._text)
        p.end()


# ─────────────────────────────────────────────
# 즐겨찾기 저장 경로
# ─────────────────────────────────────────────

import paths as _paths
_FAVE_PATH: Path = _paths.BASE_DIR / "favorites.json" 

EASTER_EGGS = [
    "루미아섬 접속 시도 중...",
    "이 프로그램의 제작자는 니나마무입니다",
    "Claude AI와 함께 만들어졌습니다",
    "나쟈에게 커피를 건네는 중...",
    "원래는 재생바 조절이 가능했는데 버그나서 사라졌습니다.",
    "요즘 시셀라가 재밌더라구요.",
    "최적의 비트레이트를 탐색 중...",
    "문제 발생 시 Discord: ready22 (친추 필수)",
    "젠장 클로에! 난 네가 좋다!",
    "플레이리스트에 영혼을 담는 중...",
    "NINAMAMU — All rights reserved",
    "오늘의 선곡은 운명이 결정합니다.",
    "Made with Claude AI & too much caffeine",
    "큐를 정렬하는 중... (실은 그냥 셔플)",
    "이터니티를 찍는 그날까지.",
    "더 작고, 더 빠르고, 더 둥글게.",
    "오늘도 좋은 방송 되세요.",
    "의외로 하트는 키가 크다.",
    "방송할 때 화면캡쳐로 위젯을 띄워서 쓰면 좋습니다. (누르면 가운데에 뜸)",
    "행사장에서 알파 코스어를 본다면 니나마무일 확률이 높습니다.",
    "이터널리턴 니나마무 친구신청 받습니다",
    "ready22에게 버그 제보 환영합니다",
    "지금 재생 중인 곡, 마음에 드시나요?",
]


# ─────────────────────────────────────────────
# 즐겨찾기 데이터 (영구 저장)
# ─────────────────────────────────────────────

def load_favorites() -> List[dict]:
    try:
        if _FAVE_PATH.exists():
            return json.loads(_FAVE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def save_favorites(items: List[dict]):
    try:
        _FAVE_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# ─────────────────────────────────────────────
# 볼륨 영구 저장
# ─────────────────────────────────────────────
_VOL_PATH: Path = _paths.BASE_DIR / "volume.json"
_DEFAULT_VOLUME = 15

def load_volume() -> int:
    try:
        if _VOL_PATH.exists():
            data = json.loads(_VOL_PATH.read_text(encoding="utf-8"))
            return max(0, min(100, int(data.get("volume", _DEFAULT_VOLUME))))
    except Exception:
        pass
    return _DEFAULT_VOLUME

def save_volume(val: int):
    try:
        _VOL_PATH.write_text(json.dumps({"volume": val}), encoding="utf-8")
    except Exception:
        pass


def fave_from_track(track: Track) -> dict:
    return {
        "title": track.title,
        "url": track.url,
        "duration": track.duration,
        "thumbnail": track.thumbnail,
        "uploader": track.uploader,
        "source_type": track.source_type,
        "is_playlist": False,
    }


def fave_from_playlist(url: str, title: str, count: int) -> dict:
    """플레이리스트 URL 전체를 즐겨찾기 단일 항목으로 저장"""
    return {
        "title": title,
        "url": url,
        "duration": 0,
        "thumbnail": "",
        "uploader": f"{count}곡",
        "source_type": "youtube",
        "is_playlist": True,
    }


def fave_from_query(query: str) -> dict:
    """URL/검색어를 즐겨찾기 항목으로 저장 (플레이리스트 등)"""
    is_pl = "list=" in query
    return {
        "title": query,
        "url": query,
        "duration": 0,
        "thumbnail": "",
        "uploader": "",
        "source_type": "youtube",
        "is_playlist": is_pl,
    }


def track_from_fave(f: dict) -> Track:
    return Track(
        title=f.get("title", "제목 없음"),
        url=f.get("url", ""),
        duration=f.get("duration", 0),
        thumbnail=f.get("thumbnail", ""),
        uploader=f.get("uploader", ""),
        source_type=f.get("source_type", "youtube"),
    )


# ─────────────────────────────────────────────
# 검색 워커
# ─────────────────────────────────────────────

class SearchSignals(QObject):
    results = pyqtSignal(list)
    error   = pyqtSignal(str)
    done    = pyqtSignal()


class SearchRunnable(QRunnable):
    def __init__(self, query: str):
        super().__init__()
        self.query = query
        self.signals = SearchSignals()
        self.setAutoDelete(True)

    @pyqtSlot()
    def run(self):
        try:
            tracks = search_youtube(self.query)
            self.signals.results.emit(tracks)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.done.emit()


class ThumbSignals(QObject):
    loaded = pyqtSignal(str, QPixmap)


class ThumbRunnable(QRunnable):
    def __init__(self, url: str, thumb_url: str):
        super().__init__()
        self.url = url
        self.thumb_url = thumb_url
        self.signals = ThumbSignals()
        self.setAutoDelete(True)

    @pyqtSlot()
    def run(self):
        try:
            data = urllib.request.urlopen(self.thumb_url, timeout=5).read()
            img = QImage()
            img.loadFromData(data)
            px = QPixmap.fromImage(img).scaled(
                60, 45,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.signals.loaded.emit(self.url, px)
        except Exception:
            pass


# ─────────────────────────────────────────────
# 즐겨찾기 아이템 위젯
# ─────────────────────────────────────────────

class FavoriteItemWidget(QWidget):
    def __init__(self, fave: dict, theme: Theme, idx: int):
        super().__init__()
        self.fave = fave
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        num = QLabel(f"{idx + 1}")
        num.setFixedWidth(18)
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num.setStyleSheet(f"color:{theme.muted}; font-size:9px;")
        layout.addWidget(num)

        is_playlist = fave.get("is_playlist", False) or "list=" in fave.get("url", "")
        icon_lbl = QLabel("≡" if is_playlist else "★")
        icon_lbl.setFixedWidth(14)
        icon_lbl.setStyleSheet(
            f"color:{theme.accent2}; font-size:12px; font-weight:bold;" if is_playlist
            else f"color:{theme.accent}; font-size:10px;"
        )
        layout.addWidget(icon_lbl)

        info = QVBoxLayout()
        info.setSpacing(1)
        info.setContentsMargins(0, 0, 0, 0)
        info.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title = fave.get("title", "제목 없음")
        t_lbl = QLabel(title)
        t_lbl.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Medium))
        fm = t_lbl.fontMetrics()
        t_lbl.setText(fm.elidedText(title, Qt.TextElideMode.ElideRight, 260))
        t_lbl.setStyleSheet(f"color:{theme.text};")

        parts = []
        uploader = fave.get("uploader", "")
        duration = fave.get("duration", 0)
        if is_playlist:
            parts.append("📋 플레이리스트")
            if uploader:
                parts.append(uploader)
        else:
            if uploader: parts.append(uploader)
            if duration:
                m, s = divmod(duration, 60)
                parts.append(f"{m}:{s:02d}")

        m_lbl = QLabel("  ·  ".join(parts) if parts else "즐겨찾기")
        m_lbl.setStyleSheet(f"color:{theme.muted}; font-size:9px;")

        info.addWidget(t_lbl)
        info.addWidget(m_lbl)
        layout.addLayout(info, 1)


# ─────────────────────────────────────────────
# 검색 결과 아이템
# ─────────────────────────────────────────────

class SearchResultWidget(QWidget):
    def __init__(self, track: Track, theme: Theme):
        super().__init__()
        self.track = track
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.thumb = QLabel()
        self.thumb.setFixedSize(60, 45)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setStyleSheet(
            f"background:{theme.surface}; border-radius:4px; border:1px solid {theme.border};"
        )
        px = IC.icon("music_note", theme.muted, 26)
        self.thumb.setPixmap(px)
        layout.addWidget(self.thumb)

        info = QVBoxLayout()
        info.setSpacing(1)
        info.setContentsMargins(0, 0, 0, 0)
        info.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        t_lbl = QLabel(track.title)
        t_lbl.setFont(QFont("Malgun Gothic", 11, QFont.Weight.Medium))
        fm = t_lbl.fontMetrics()
        t_lbl.setText(fm.elidedText(track.title, Qt.TextElideMode.ElideRight, 280))
        t_lbl.setStyleSheet(f"color:{theme.text};")

        parts = []
        if track.uploader: parts.append(track.uploader)
        if track.duration: parts.append(track.duration_str())
        m_lbl = QLabel("  ·  ".join(parts))
        m_lbl.setStyleSheet(f"color:{theme.muted}; font-size:10px;")

        info.addWidget(t_lbl)
        info.addWidget(m_lbl)
        layout.addLayout(info, 1)

    def set_thumbnail(self, px: QPixmap):
        self.thumb.setPixmap(
            px.scaled(60, 45, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                      Qt.TransformationMode.SmoothTransformation)
        )
        self.thumb.setScaledContents(True)
        self.thumb.setStyleSheet("border-radius:4px; border:none;")


# ─────────────────────────────────────────────
# 큐 아이템
# ─────────────────────────────────────────────

class QueueItemWidget(QWidget):
    def __init__(self, track: Track, index: int, theme: Theme, is_current=False):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 3, 10, 3)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        num = QLabel("▶" if is_current else str(index + 1))
        num.setFixedWidth(20)
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        num.setStyleSheet(
            f"color:{theme.accent}; font-size:11px; font-weight:bold;" if is_current
            else f"color:{theme.muted}; font-size:10px;"
        )
        layout.addWidget(num)

        t_lbl = QLabel(track.title)
        fm = t_lbl.fontMetrics()
        t_lbl.setText(fm.elidedText(track.title, Qt.TextElideMode.ElideRight, 240))
        t_lbl.setStyleSheet(
            f"color:{theme.accent}; font-size:12px; font-weight:600;" if is_current
            else f"color:{theme.text}; font-size:12px;"
        )
        t_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        layout.addWidget(t_lbl)

        if track.duration:
            dur = QLabel(track.duration_str())
            dur.setStyleSheet(f"color:{theme.muted}; font-size:10px; font-family:Consolas;")
            dur.setFixedWidth(44)
            dur.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            layout.addWidget(dur)


# ─────────────────────────────────────────────
# 업데이터 패널 (이스터에그)
# ─────────────────────────────────────────────

class UpdatePanel(QWidget):
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(8)

        self._log = QLabel("도구 버전 확인 중...")
        self._log.setStyleSheet(f"color:{theme.muted}; font-size:9px;")
        self._log.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addStretch()
        layout.addWidget(self._log)

    def set_log(self, msg: str):
        self._log.setText(msg)

    def mark_done(self):
        self._log.setText("✓ 준비 완료")


# ─────────────────────────────────────────────
# 진행바 — 표시 전용 (마우스 인터랙션 없음)
# ─────────────────────────────────────────────

class ProgressSlider(QSlider):
    seek_requested = pyqtSignal(int)   # 호환성 유지 (미사용)

    def __init__(self):
        super().__init__(Qt.Orientation.Horizontal)
        self.setRange(0, 1000)
        self._dragging = False  # 항상 False, 호환성 유지

    def mousePressEvent(self, e): e.ignore()
    def mouseReleaseEvent(self, e): e.ignore()
    def mouseMoveEvent(self, e): e.ignore()
    def wheelEvent(self, e): e.ignore()


# ─────────────────────────────────────────────
# 테마 다이얼로그
# ─────────────────────────────────────────────

class ThemeDialog(QDialog):
    theme_selected = pyqtSignal(object)

    def __init__(self, current: Theme, parent=None):
        super().__init__(parent)
        self.setWindowTitle("테마 선택")
        self.setFixedSize(420, 310)
        self._custom = Theme(**{k: getattr(current, k) for k in Theme.__dataclass_fields__})
        self._custom.name = "커스텀"

        L = QVBoxLayout(self)
        L.setSpacing(10)
        hdr = QLabel("테마 선택")
        hdr.setFont(QFont("Malgun Gothic", 13, QFont.Weight.Bold))
        L.addWidget(hdr)

        grid = QGridLayout()
        grid.setSpacing(7)
        for i, (name, th) in enumerate(PRESETS.items()):
            btn = QPushButton(name)
            btn.setFixedHeight(38)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background:{th.header_bg}; color:{th.header_text};
                    border-radius:8px; font-size:11px; font-weight:bold; border:none;
                }}
                QPushButton:hover {{ border:2px solid {th.accent2}; }}
            """)
            btn.clicked.connect(lambda _, t=th: self._pick(t))
            grid.addWidget(btn, i // 3, i % 3)
        L.addLayout(grid)

        L.addWidget(_divider())
        cust_hdr = QLabel("커스텀 색상")
        cust_hdr.setFont(QFont("Malgun Gothic", 11, QFont.Weight.Bold))
        L.addWidget(cust_hdr)

        color_row = QHBoxLayout()
        self._cbtns: dict = {}
        for field, label in [("bg","배경"),("surface","카드"),("accent","강조"),
                              ("accent2","보조"),("text","텍스트"),("header_bg","헤더")]:
            cb = QPushButton(label)
            cb.setFixedHeight(26)
            c = getattr(self._custom, field)
            cb.setStyleSheet(
                f"background:{c}; color:{'#fff' if _dark(c) else '#000'};"
                f"border-radius:5px; font-size:10px; border:1px solid #aaa;"
            )
            cb.clicked.connect(lambda _, f=field: self._pick_color(f))
            color_row.addWidget(cb)
            self._cbtns[field] = cb
        L.addLayout(color_row)

        apply_btn = QPushButton("커스텀 적용")
        apply_btn.setFixedHeight(32)
        apply_btn.clicked.connect(lambda: self._pick(self._custom))
        L.addWidget(apply_btn)

    def _pick_color(self, field: str):
        c = QColorDialog.getColor(QColor(getattr(self._custom, field)), self)
        if c.isValid():
            hex_c = c.name()
            setattr(self._custom, field, hex_c)
            if field == "accent":
                self._custom.header_bg = hex_c
                if "header_bg" in self._cbtns:
                    self._update_cbtn(self._cbtns["header_bg"], hex_c)
            self._update_cbtn(self._cbtns[field], hex_c)

    def _update_cbtn(self, btn: QPushButton, hex_c: str):
        btn.setStyleSheet(
            f"background:{hex_c}; color:{'#fff' if _dark(hex_c) else '#000'};"
            f"border-radius:5px; font-size:10px; border:1px solid #aaa;"
        )

    def _pick(self, theme: Theme):
        self.theme_selected.emit(theme)
        self.accept()


# ─────────────────────────────────────────────
# 메인 창
# ─────────────────────────────────────────────

class MainWindow(QMainWindow):
    sig_track_start  = pyqtSignal(object)
    sig_track_end    = pyqtSignal()
    sig_queue_update = pyqtSignal()
    sig_error        = pyqtSignal(str)
    sig_resolving    = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.player    = EMAGPlayer()
        self.theme     = load_theme()
        self._widget: Optional[StreamWidget] = None
        self._thumb_map: dict = {}
        self._pool     = QThreadPool.globalInstance()
        self._pool.setMaxThreadCount(6)
        self._searching = False
        self._favorites: List[dict] = load_favorites()
        self._last_search_query = ""

        self._setup_player_callbacks()
        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self._start_timer()
        self.setAcceptDrops(True)
        self._run_updater()
        self._refresh_favorites()

    # ── 초기화 ──

    def _setup_window(self):
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(440, 620)
        self.setStyleSheet(build_stylesheet(self.theme))
        self._restore_geometry()

    # ── geometry 저장/복원 ──

    _GEO_PATH = _paths.BASE_DIR / "window_geometry.json"

    def _restore_geometry(self):
        try:
            data = json.loads(self._GEO_PATH.read_text(encoding="utf-8"))
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen().availableGeometry()
            x = max(0, min(data["x"], screen.width()  - 100))
            y = max(0, min(data["y"], screen.height() - 100))
            w = max(440, min(data["w"], screen.width()))
            h = max(620, min(data["h"], screen.height()))
            self.setGeometry(x, y, w, h)
        except Exception:
            self.resize(460, 720)

    def _save_geometry(self):
        try:
            g = self.geometry()
            self._GEO_PATH.write_text(
                json.dumps({"x": g.x(), "y": g.y(), "w": g.width(), "h": g.height()}),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _setup_player_callbacks(self):
        self.player.on_track_start  = lambda t: self.sig_track_start.emit(t)
        self.player.on_track_end    = lambda:   self.sig_track_end.emit()
        self.player.on_queue_update = lambda:   self.sig_queue_update.emit()
        self.player.on_error        = lambda e: self.sig_error.emit(e)
        self.player.on_resolving    = lambda b: self.sig_resolving.emit(b)
        self.player.on_thumb_update = lambda t: self._on_thumb_update(t)

    # ── 창 닫기 ──

    def closeEvent(self, event: QCloseEvent):
        self._save_geometry()
        self.player.stop()
        kill_all_ffmpeg()
        if self._widget:
            self._widget.close()
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()
        event.accept()

    # ── UI 빌드 ──

    def _build_ui(self):
        t = self.theme
        root = QWidget()
        self.setCentralWidget(root)
        M = QVBoxLayout(root)
        M.setContentsMargins(10, 10, 10, 10)
        M.setSpacing(7)

        # ── 헤더 ──
        hdr = QWidget()
        hdr.setFixedHeight(42)
        hdr.setStyleSheet(f"background:{t.header_bg}; border-radius:10px;")
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(14, 0, 10, 0)
        hl.setSpacing(6)

        self._logo = QLabel(APP_NAME)
        self._logo.setStyleSheet(
            f"color:{t.header_text}; font-size:12px; font-weight:bold;"
        )
        hl.addWidget(self._logo)
        hl.addStretch()

        # 마퀴 문구 (오른쪽→왼쪽 스크롤)
        self._phrase_label = MarqueeLabel()
        self._phrase_label.set_style(color="#ffffff", font_size=10)
        self._phrase_label.setFixedHeight(20)
        self._phrase_list = EASTER_EGGS[:]
        random.shuffle(self._phrase_list)
        self._phrase_idx = 0
        hl.addWidget(self._phrase_label, 1)

        self._phrase_timer = QTimer(self)
        self._phrase_timer.timeout.connect(self._next_phrase)
        self._phrase_timer.start(30000)

        self._status_dot   = QLabel("●")
        self._status_label = QLabel("대기 중")
        self._status_dot.setStyleSheet("color:rgba(255,255,255,0.4); font-size:8px;")
        self._status_label.setStyleSheet("color:rgba(255,255,255,0.75); font-size:10px;")
        hl.addWidget(self._status_dot)
        hl.addWidget(self._status_label)

        self._widget_btn = QPushButton()
        self._widget_btn.setFixedSize(32, 28)
        self._widget_btn.setStyleSheet(
            "background:rgba(255,255,255,0.18); border:none; border-radius:6px;"
        )
        IC.set_icon(self._widget_btn, "widget", t.header_text, 16)
        self._widget_btn.setToolTip("스트리밍 위젯 ON/OFF")

        self._theme_btn = QPushButton()
        self._theme_btn.setFixedSize(32, 28)
        self._theme_btn.setStyleSheet(
            "background:rgba(255,255,255,0.18); border:none; border-radius:6px;"
        )
        IC.set_icon(self._theme_btn, "palette", t.header_text, 16)
        self._theme_btn.setToolTip("테마 선택")

        hl.addWidget(self._widget_btn)
        hl.addWidget(self._theme_btn)
        M.addWidget(hdr)

        # 레이아웃 확정 후 텍스트 세팅
        QTimer.singleShot(50, lambda: self._phrase_label.setText(self._phrase_list[0]))

        # ── 이스터에그 패널 ──
        self._update_panel = UpdatePanel(t)
        M.addWidget(self._update_panel)

        # ── 검색창 ──
        sr = QHBoxLayout()
        sr.setSpacing(6)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("검색어 또는 유튜브 URL / 플레이리스트  (Enter)")
        self.search_input.setMinimumHeight(36)
        sr.addWidget(self.search_input)

        self.search_btn = QPushButton()
        self.search_btn.setObjectName("accent")
        self.search_btn.setFixedSize(56, 36)
        IC.set_icon(self.search_btn, "search", t.header_text, 18)
        sr.addWidget(self.search_btn)

        self.file_btn = QPushButton()
        self.file_btn.setFixedSize(36, 36)
        self.file_btn.setToolTip("로컬 파일 추가")
        IC.set_icon(self.file_btn, "folder", t.accent, 18)
        sr.addWidget(self.file_btn)
        M.addLayout(sr)

        # ── 즐겨찾기 섹션 ──
        fh = QHBoxLayout()
        fl = QLabel("즐겨찾기")
        fl.setObjectName("section")
        self.fave_count = QLabel("0")
        self.fave_count.setStyleSheet(f"color:{t.muted}; font-size:10px;")
        fave_clr_btn = QPushButton("선택 삭제")
        fave_clr_btn.setFixedHeight(22)
        fave_clr_btn.setStyleSheet(
            f"background:transparent; border:1px solid {t.border};"
            f"color:{t.muted}; font-size:10px; border-radius:4px; padding:0 8px;"
        )
        fave_clr_btn.clicked.connect(self._remove_selected_favorite)
        fh.addWidget(fl)
        fh.addWidget(self.fave_count)
        fh.addStretch()
        fh.addWidget(fave_clr_btn)
        M.addLayout(fh)

        self.fave_list = QListWidget()
        self.fave_list.setObjectName("search_results")
        self.fave_list.setFixedHeight(140)
        self.fave_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.fave_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.fave_list.customContextMenuRequested.connect(self._fave_ctx)
        placeholder = QListWidgetItem("즐겨찾기가 없습니다  (검색 후 우클릭으로 추가)")
        placeholder.setForeground(QColor(t.muted))
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        self.fave_list.addItem(placeholder)
        M.addWidget(self.fave_list)

        M.addWidget(_divider())

        # ── NOW PLAYING 패널 ──
        now = QFrame()
        now.setProperty("role", "panel")
        np = QVBoxLayout(now)
        np.setContentsMargins(14, 10, 14, 10)
        np.setSpacing(5)

        nph = QHBoxLayout()
        np_lbl = QLabel("NOW PLAYING")
        np_lbl.setObjectName("section")
        nph.addWidget(np_lbl)
        nph.addStretch()

        self._loading_lbl = QLabel("로딩 중...")
        self._loading_lbl.setStyleSheet(f"color:{t.accent}; font-size:10px;")
        self._loading_lbl.hide()
        nph.addWidget(self._loading_lbl)

        self.repeat_btn     = _mk_icon_btn("repeat", t.muted, t, 28, "한 곡 반복")
        self.repeat_all_btn = _mk_icon_btn("repeat", t.muted, t, 28, "전체 반복")
        nph.addWidget(self.repeat_btn)
        nph.addWidget(self.repeat_all_btn)
        np.addLayout(nph)

        self.now_title = QLabel("재생 중인 곡 없음")
        self.now_title.setObjectName("title")
        self.now_title.setWordWrap(True)
        self.now_uploader = QLabel("")
        self.now_uploader.setObjectName("subtitle")
        np.addWidget(self.now_title)
        np.addWidget(self.now_uploader)

        self.progress = ProgressSlider()
        self.progress.setEnabled(False)
        np.addWidget(self.progress)

        tr = QHBoxLayout()
        self.time_cur = QLabel("0:00")
        self.time_cur.setObjectName("time")
        self.time_tot = QLabel("0:00")
        self.time_tot.setObjectName("time")
        tr.addWidget(self.time_cur); tr.addStretch(); tr.addWidget(self.time_tot)
        np.addLayout(tr)

        # 컨트롤 행
        ctrl = QHBoxLayout()
        ctrl.setSpacing(6)
        ctrl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        self.shuffle_btn = _mk_icon_btn("shuffle", t.muted, t, 36, "셔플")
        self.prev_btn    = _mk_icon_btn("prev",    t.muted, t, 36, "이전")
        self.next_btn    = _mk_icon_btn("next",    t.muted, t, 36, "다음")
        self.stop_btn    = _mk_icon_btn("stop",    t.muted, t, 36, "정지")

        self.play_btn = QPushButton()
        self.play_btn.setFixedSize(48, 48)
        self.play_btn.setStyleSheet(f"""
            QPushButton {{ background:{t.accent}; border:none; border-radius:24px; }}
            QPushButton:hover {{ background:{t.accent2}; }}
        """)
        IC.set_icon(self.play_btn, "play", t.header_text, 24)

        for w in [self.shuffle_btn, self.prev_btn, self.play_btn,
                  self.next_btn, self.stop_btn]:
            ctrl.addWidget(w)
        np.addLayout(ctrl)

        # 볼륨
        vr = QHBoxLayout()
        vr.setContentsMargins(0, 2, 0, 0)
        vr.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        vol_icon = QPushButton()
        vol_icon.setFixedSize(22, 22)
        vol_icon.setStyleSheet("background:transparent; border:none;")
        IC.set_icon(vol_icon, "volume", t.muted, 16)
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        _saved_vol = load_volume()
        self.vol_slider.setValue(_saved_vol)
        self.vol_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.vol_label = QLabel(f"{_saved_vol}%")
        self.vol_label.setObjectName("time")
        self.vol_label.setFixedWidth(34)
        self.vol_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        vr.addWidget(vol_icon)
        vr.addWidget(self.vol_slider, 1)
        vr.addWidget(self.vol_label)
        np.addLayout(vr)
        M.addWidget(now)

        # ── 큐 섹션 ──
        qh = QHBoxLayout()
        ql = QLabel("QUEUE")
        ql.setObjectName("section")
        self.queue_count = QLabel("0곡")
        self.queue_count.setStyleSheet(f"color:{t.muted}; font-size:10px;")
        clr_btn = QPushButton("전체 삭제")
        clr_btn.setFixedHeight(22)
        clr_btn.setStyleSheet(
            f"background:transparent; border:1px solid {t.border};"
            f"color:{t.muted}; font-size:10px; border-radius:4px; padding:0 8px;"
        )
        clr_btn.clicked.connect(self._clear_queue)
        qh.addWidget(ql); qh.addWidget(self.queue_count)
        qh.addStretch(); qh.addWidget(clr_btn)
        M.addLayout(qh)

        self.queue_list = QListWidget()
        self.queue_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.queue_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.queue_list.customContextMenuRequested.connect(self._queue_ctx)
        self.queue_list.itemDoubleClicked.connect(self._queue_dclick)
        M.addWidget(self.queue_list)

    # ── 신호 연결 ──

    def _connect_signals(self):
        self.search_btn.clicked.connect(self._do_search)
        self.search_input.returnPressed.connect(self._do_search)
        self.file_btn.clicked.connect(self._open_file)
        self.fave_list.itemDoubleClicked.connect(self._fave_dclick)

        self.play_btn.clicked.connect(self._toggle_play)
        self.next_btn.clicked.connect(lambda: self.player.skip())
        self.prev_btn.clicked.connect(self._prev)
        self.stop_btn.clicked.connect(self._stop)
        self.shuffle_btn.clicked.connect(self._shuffle)
        self.repeat_btn.clicked.connect(self._toggle_repeat)
        self.repeat_all_btn.clicked.connect(self._toggle_repeat_all)
        self.vol_slider.valueChanged.connect(self._vol_changed)
        self.progress.seek_requested.connect(self._on_seek)

        self._widget_btn.clicked.connect(self._toggle_widget)
        self._theme_btn.clicked.connect(self._open_theme_dialog)

        self.sig_track_start.connect(self._on_track_start)
        self.sig_track_end.connect(self._on_track_end)
        self.sig_queue_update.connect(self._refresh_queue)
        self.sig_error.connect(self._show_error)
        self.sig_resolving.connect(self._on_resolving)

    def _start_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(500)

    def _tick(self):
        if not (self.player.is_playing or self.player.is_paused):
            return
        track = self.player.queue.current
        if not track or not track.duration:
            return
        elapsed = self.player.elapsed()
        if not self.progress._dragging:
            self.progress.setValue(int((elapsed / track.duration) * 1000))
        self.time_cur.setText(_fmt_time(int(elapsed)))

    # ── seek (시그널 연결은 유지, 실제론 호출 안 됨) ──

    def _on_seek(self, val: int):
        track = self.player.queue.current
        if not track or not track.duration:
            return
        pos = (val / 1000) * track.duration
        self.player.seek(pos)
        self.time_cur.setText(_fmt_time(int(pos)))

    # ── 업데이터 ──

    def _run_updater(self):
        def on_log(msg): self._update_panel.set_log(msg)
        def on_done():
            self._update_panel.mark_done()
            QTimer.singleShot(8000, self._update_panel.hide)
        run_updates_async(on_log=on_log, on_done=on_done)

    # ── 위젯 ──

    def _toggle_widget(self):
        if self._widget and self._widget.isVisible():
            self._widget.hide()
        else:
            if not self._widget:
                self._widget = StreamWidget(self.theme, self.player)
                self._widget._GEO_PATH = _paths.BASE_DIR / "widget_geometry.json"
                self._widget._restore_geometry()
                self._widget.closed.connect(lambda: None)
            if self.player.queue.current:
                self._widget.update_track(self.player.queue.current)
                self._widget.update_play_btn(self.player.is_playing)
            self._widget.show()

    # ── 테마 ──

    def _open_theme_dialog(self):
        dlg = ThemeDialog(self.theme, self)
        dlg.theme_selected.connect(self._apply_new_theme)
        dlg.exec()

    def _apply_new_theme(self, theme: Theme):
        self.theme = theme
        save_theme(theme)
        self.setStyleSheet(build_stylesheet(theme))
        if self._widget:
            self._widget.apply_theme(theme)
        self._logo.parent().setStyleSheet(
            f"background:{theme.header_bg}; border-radius:10px;"
        )
        IC.set_icon(self.search_btn,   "search",  theme.header_text, 18)
        IC.set_icon(self.file_btn,     "folder",  theme.accent,      18)
        IC.set_icon(self._widget_btn,  "widget",  theme.header_text, 16)
        IC.set_icon(self._theme_btn,   "palette", theme.header_text, 16)
        IC.set_icon(self.play_btn,     "play",    theme.header_text, 24)
        self.play_btn.setStyleSheet(f"""
            QPushButton {{ background:{theme.accent}; border:none; border-radius:24px; }}
            QPushButton:hover {{ background:{theme.accent2}; }}
        """)
        self._refresh_queue()
        self._refresh_favorites()

    # ── 검색 ──

    def _do_search(self):
        if self._searching:
            return
        query = self.search_input.text().strip()
        if not query:
            return

        self._last_search_query = query
        self._searching = True
        self._set_status("검색 중...", active=True)
        self.search_btn.setEnabled(False)

        runnable = SearchRunnable(query)
        runnable.signals.results.connect(self._on_search_results)
        runnable.signals.error.connect(self._show_error)
        runnable.signals.done.connect(self._on_search_done)
        self._pool.start(runnable)

    def _on_search_done(self):
        self._searching = False
        self.search_btn.setEnabled(True)
        self._set_status("대기 중")
        self.search_input.clear()

    def _on_search_results(self, tracks: list):
        if not tracks:
            self._set_status("결과 없음")
            return

        query = self._last_search_query
        is_playlist_query = "list=" in query and query.startswith("http")

        if len(tracks) == 1:
            self.player.add_and_play(tracks[0])
            self._set_status(f"재생: {tracks[0].title[:28]}")
        else:
            self.player.add_many(tracks)
            self._set_status(f"플레이리스트 {len(tracks)}곡 추가")
            if is_playlist_query:
                self._offer_playlist_favorite(query, tracks)

        self._refresh_queue()

    def _offer_playlist_favorite(self, url: str, tracks: list):
        existing_urls = {f.get("url", "") for f in self._favorites}
        if url in existing_urls:
            return
        title = f"[플레이리스트] {tracks[0].title[:28]}… 외 {len(tracks)-1}곡" if len(tracks) > 1 else tracks[0].title
        fave = fave_from_playlist(url, title, len(tracks))
        self._favorites.append(fave)
        save_favorites(self._favorites)
        self._refresh_favorites()
        self._set_status(f"즐겨찾기에 플레이리스트 저장 ({len(tracks)}곡)")

    def _search_dclick(self, item: QListWidgetItem):
        track = item.data(Qt.ItemDataRole.UserRole)
        if track:
            self.player.add_and_play(track)
            self._set_status(f"추가: {track.title[:28]}")

    # ── 즐겨찾기 ──

    def _refresh_favorites(self):
        self.fave_list.clear()
        if not self._favorites:
            placeholder = QListWidgetItem("즐겨찾기가 없습니다  (검색 후 우클릭으로 추가)")
            placeholder.setForeground(QColor(self.theme.muted))
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.fave_list.addItem(placeholder)
            self.fave_count.setText("0")
            return
        for i, fave in enumerate(self._favorites):
            item = QListWidgetItem(self.fave_list)
            w = FavoriteItemWidget(fave, self.theme, i)
            item.setSizeHint(QSize(0, 46))
            self.fave_list.setItemWidget(item, w)
            item.setData(Qt.ItemDataRole.UserRole, i)
        self.fave_count.setText(str(len(self._favorites)))

    def _fave_dclick(self, item: QListWidgetItem):
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is None:
            return
        fave = self._favorites[idx]
        url = fave.get("url", "")
        if not url:
            return
        is_playlist = fave.get("is_playlist", False) or "list=" in url
        if is_playlist:
            self._set_status("플레이리스트 로딩 중...", active=True)
            def _load_pl():
                tracks = fetch_playlist(url)
                if tracks:
                    self.player.add_many(tracks)
                    self._set_status(f"플레이리스트 {len(tracks)}곡 추가")
                else:
                    self._set_status("로딩 실패")
            threading.Thread(target=_load_pl, daemon=True).start()
        else:
            track = track_from_fave(fave)
            self.player.add_and_play(track)
            self._set_status(f"재생: {track.title[:28]}")

    def _fave_ctx(self, pos: QPoint):
        item = self.fave_list.itemAt(pos)
        if not item: return
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is None: return
        menu = QMenu(self)
        menu.addAction("재생", lambda: self._fave_dclick(item))
        menu.addSeparator()
        menu.addAction("즐겨찾기에서 제거", lambda: self._remove_favorite(idx))
        menu.exec(self.fave_list.mapToGlobal(pos))

    def _add_favorite_from_query(self, query: str, tracks: List[Track]):
        if not query:
            return
        existing_urls = {f.get("url", "") for f in self._favorites}
        if "list=" in query or query.startswith("http"):
            fave = fave_from_query(query)
            if tracks:
                fave["title"] = f"[플레이리스트] {tracks[0].title[:30]}... 외 {len(tracks)-1}곡" if len(tracks) > 1 else tracks[0].title
        else:
            if not tracks:
                return
            fave = fave_from_track(tracks[0])
        if fave["url"] not in existing_urls:
            self._favorites.append(fave)
            save_favorites(self._favorites)
            self._refresh_favorites()

    def _remove_favorite(self, idx: int):
        if 0 <= idx < len(self._favorites):
            self._favorites.pop(idx)
            save_favorites(self._favorites)
            self._refresh_favorites()

    def _remove_selected_favorite(self):
        items = self.fave_list.selectedItems()
        indices = sorted(
            [i.data(Qt.ItemDataRole.UserRole) for i in items
             if i.data(Qt.ItemDataRole.UserRole) is not None],
            reverse=True
        )
        for idx in indices:
            if 0 <= idx < len(self._favorites):
                self._favorites.pop(idx)
        save_favorites(self._favorites)
        self._refresh_favorites()

    def _add_current_to_favorites(self):
        track = self.player.queue.current
        if not track:
            return
        existing_urls = {f.get("url", "") for f in self._favorites}
        if track.url in existing_urls:
            self._set_status("이미 즐겨찾기에 있습니다")
            return
        self._favorites.append(fave_from_track(track))
        save_favorites(self._favorites)
        self._refresh_favorites()
        self._set_status(f"즐겨찾기 추가: {track.title[:28]}")

    # ── 파일 / 드래그앤드롭 ──

    def _open_file(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "오디오 파일 열기", "",
            "Audio (*.mp3 *.flac *.wav *.m4a *.ogg *.opus *.aac *.wma);;All (*)"
        )
        for f in files:
            self.player.add_and_play(file_to_track(f))

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls() or e.mimeData().hasText():
            e.acceptProposedAction()

    def dropEvent(self, e: QDropEvent):
        if e.mimeData().hasUrls():
            for url in e.mimeData().urls():
                path = url.toLocalFile()
                if path:
                    self.player.add_and_play(file_to_track(path))
                else:
                    web = url.toString()
                    if "youtube" in web or "youtu.be" in web:
                        self.search_input.setText(web)
                        self._do_search()
        elif e.mimeData().hasText():
            self.search_input.setText(e.mimeData().text().strip())
            self._do_search()

    # ── 컨트롤 ──

    def _toggle_play(self):
        if self.player.is_playing:
            self.player.pause()
            IC.set_icon(self.play_btn, "play",  self.theme.header_text, 24)
            self._set_status("일시정지")
            if self._widget: self._widget.update_play_btn(False)
        elif self.player.is_paused:
            self.player.resume()
            IC.set_icon(self.play_btn, "pause", self.theme.header_text, 24)
            self._set_status("재생 중", active=True)
            if self._widget: self._widget.update_play_btn(True)
        else:
            if self.player.queue.peek_next():
                self.player.play_next()

    def _prev(self):
        if self.player.queue.current:
            self.player.play_track(self.player.queue.current)

    def _stop(self):
        self.player.stop()
        self.player.queue.clear()
        IC.set_icon(self.play_btn, "play", self.theme.header_text, 24)
        self.now_title.setText("재생 중인 곡 없음")
        self.now_uploader.setText("")
        self.progress.setValue(0); self.progress.setEnabled(False)
        self.time_cur.setText("0:00"); self.time_tot.setText("0:00")
        self._set_status("정지")
        self._refresh_queue()
        if self._widget: self._widget.update_idle()

    def _shuffle(self):
        self.player.queue.shuffle()
        self._refresh_queue()

    def _toggle_repeat(self):
        self.player.queue.repeat = not self.player.queue.repeat
        active = self.player.queue.repeat
        IC.set_icon(self.repeat_btn,
                    "repeat_one" if active else "repeat",
                    self.theme.accent if active else self.theme.muted, 16)

    def _toggle_repeat_all(self):
        self.player.queue.repeat_all = not self.player.queue.repeat_all
        active = self.player.queue.repeat_all
        IC.set_icon(self.repeat_all_btn, "repeat",
                    self.theme.accent if active else self.theme.muted, 16)

    def _vol_changed(self, val: int):
        self.vol_label.setText(f"{val}%")
        self.player.set_volume(val / 100)
        save_volume(val)

    def _clear_queue(self):
        self.player.queue.clear()
        self._refresh_queue()

    # ── 큐 ──

    def _refresh_queue(self):
        tracks = self.player.queue.list()
        self.queue_list.clear()
        self.queue_count.setText(f"{len(tracks)}곡")
        for i, track in enumerate(tracks):
            item = QListWidgetItem(self.queue_list)
            w = QueueItemWidget(track, i, self.theme)
            item.setSizeHint(QSize(0, 40))
            self.queue_list.setItemWidget(item, w)
            item.setData(Qt.ItemDataRole.UserRole, i)

    def _queue_ctx(self, pos: QPoint):
        item = self.queue_list.itemAt(pos)
        if not item: return
        idx = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        menu.addAction("지금 재생", lambda: self._q_play_now(idx))
        menu.addAction("맨 위로",  lambda: self._q_top(idx))
        menu.addSeparator()
        menu.addAction("즐겨찾기 추가", lambda: self._q_add_to_fave(idx))
        menu.addSeparator()
        menu.addAction("제거",     lambda: self._q_remove(idx))
        menu.exec(self.queue_list.mapToGlobal(pos))

    def _queue_dclick(self, item: QListWidgetItem):
        self._q_play_now(item.data(Qt.ItemDataRole.UserRole))

    def _q_play_now(self, idx: int):
        tracks = self.player.queue.list()
        if 0 <= idx < len(tracks):
            track = tracks[idx]
            self.player.queue.remove(idx)
            self.player.play_track(track)
            self._refresh_queue()

    def _q_remove(self, idx: int):
        self.player.queue.remove(idx)
        self._refresh_queue()

    def _q_top(self, idx: int):
        self.player.queue.move(idx, 0)
        self._refresh_queue()

    def _q_add_to_fave(self, idx: int):
        tracks = self.player.queue.list()
        if 0 <= idx < len(tracks):
            existing_urls = {f.get("url", "") for f in self._favorites}
            track = tracks[idx]
            if track.url in existing_urls:
                self._set_status("이미 즐겨찾기에 있습니다")
                return
            self._favorites.append(fave_from_track(track))
            save_favorites(self._favorites)
            self._refresh_favorites()
            self._set_status(f"즐겨찾기 추가: {track.title[:28]}")

    # ── 플레이어 콜백 ──

    def _on_track_start(self, track: Track):
        self.now_title.setText(track.title)
        self.now_uploader.setText(track.uploader or "")
        self.time_tot.setText(track.duration_str() if track.duration else "--:--")
        self.progress.setEnabled(True); self.progress.setValue(0)
        IC.set_icon(self.play_btn, "pause", self.theme.header_text, 24)
        self._set_status("재생 중", active=True)
        self._refresh_queue()
        if self._widget and self._widget.isVisible():
            self._widget.update_track(track)

    def _on_track_end(self):
        IC.set_icon(self.play_btn, "play", self.theme.header_text, 24)
        self.now_title.setText("재생 중인 곡 없음")
        self.now_uploader.setText("")
        self.progress.setValue(0); self.progress.setEnabled(False)
        self._set_status("대기 중")
        if self._widget: self._widget.update_idle()

    def _on_resolving(self, loading: bool):
        self._loading_lbl.setVisible(loading)
        if self._widget and self._widget.isVisible():
            if loading:
                self._widget.disk.set_spinning(True)

    def _on_thumb_update(self, track):
        if self._widget and self._widget.isVisible():
            if track.thumbnail and track.thumbnail != getattr(self._widget, '_thumb_url', None):
                self._widget._thumb_url = track.thumbnail
                threading.Thread(
                    target=self._widget._load_thumb,
                    args=(track.thumbnail,),
                    daemon=True
                ).start()

    def _show_error(self, msg: str):
        self._set_status(f"오류: {msg[:38]}")

    def _next_phrase(self):
        self._phrase_idx = (self._phrase_idx + 1) % len(self._phrase_list)
        if self._phrase_idx == 0:
            random.shuffle(self._phrase_list)
        self._phrase_label.setText(self._phrase_list[self._phrase_idx])

    def _set_status(self, text: str, active=False):
        self._status_label.setText(text)
        dot_c = "rgba(255,255,255,0.95)" if active else "rgba(255,255,255,0.4)"
        txt_c = "rgba(255,255,255,0.95)" if active else "rgba(255,255,255,0.7)"
        self._status_dot.setStyleSheet(f"color:{dot_c}; font-size:8px;")
        self._status_label.setStyleSheet(f"color:{txt_c}; font-size:10px;")


# ── 헬퍼 ──

def _mk_icon_btn(icon_name: str, color: str, t: Theme, size: int = 32, tip: str = "") -> QPushButton:
    btn = QPushButton()
    btn.setFixedSize(size, size)
    btn.setToolTip(tip)
    btn.setStyleSheet(f"""
        QPushButton {{ background:transparent; border:none; border-radius:{size//2}px; }}
        QPushButton:hover {{ background:{t.hover}; }}
        QPushButton:pressed {{ background:{t.surface2}; }}
    """)
    IC.set_icon(btn, icon_name, color, size - 10)
    return btn


def _divider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setProperty("role", "divider")
    return f


def _fmt_time(secs: int) -> str:
    m, s = divmod(secs, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _dark(hex_color: str) -> bool:
    c = QColor(hex_color)
    return (c.red() * 299 + c.green() * 587 + c.blue() * 114) < 128000