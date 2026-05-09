"""
니나마무's 플레이어 — Streaming Widget
"""

import sys, math, threading, random, urllib.request
from typing import Optional

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF, QPoint, QSize, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPainterPath, QColor, QBrush, QPen,
    QLinearGradient, QRadialGradient, QConicalGradient,
    QPixmap, QImage, QFont, QFontMetrics,
)

from theme import Theme
from player import Track
import icons as IC


def _fmt_time(secs: int) -> str:
    m, s = divmod(secs, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ─────────────────────────────────────────────
# 회전 디스크 — 시계방향, 가운데 구멍 O, 재생 중만 회전
# ─────────────────────────────────────────────

class SpinningDisk(QWidget):
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._angle = 0.0
        self._thumb: Optional[QPixmap] = None
        self._spinning = False
        self.setFixedSize(88, 88)

        self._t = QTimer(self)
        self._t.timeout.connect(self._tick)
        self._t.start(16)

    def set_thumbnail(self, px: Optional[QPixmap]):
        self._thumb = px
        self.update()

    def set_spinning(self, on: bool):
        self._spinning = on
        self.update()

    def _tick(self):
        if self._spinning:
            self._angle = (self._angle + 2.5) % 360  # 1.8 → 2.5로 더 빠르게
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.theme
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        RING  = 3.5   # 바깥 링 두께
        GAP   = 2.0   # 링-이미지 간격
        HOLE  = 10    # 가운데 구멍 반지름

        inner_r = (min(w, h) / 2) - RING - GAP
        inner_rect = QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)

        # ── 1. 회전 링 ──
        grad = QConicalGradient(QPointF(cx, cy), self._angle)
        grad.setColorAt(0.0,  QColor(t.accent))
        grad.setColorAt(0.45, QColor(t.accent2))
        grad.setColorAt(0.9,  QColor(t.accent))
        grad.setColorAt(1.0,  QColor(t.accent))
        p.setPen(QPen(QBrush(grad), RING))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(RING / 2, RING / 2, w - RING, h - RING))

        # ── 2. 썸네일 or 기본 배경 (구멍 제외한 도넛 영역) ──
        # 도넛 클립: 바깥 원 − 구멍
        donut = QPainterPath()
        donut.addEllipse(inner_rect)
        hole_rect = QRectF(cx - HOLE, cy - HOLE, HOLE * 2, HOLE * 2)
        hole_path = QPainterPath()
        hole_path.addEllipse(hole_rect)
        donut = donut.subtracted(hole_path)
        p.setClipPath(donut)

        if self._thumb:
            scaled = self._thumb.scaled(
                int(inner_rect.width()), int(inner_rect.height()),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            ox = int(inner_rect.x()) + (int(inner_rect.width())  - scaled.width())  // 2
            oy = int(inner_rect.y()) + (int(inner_rect.height()) - scaled.height()) // 2
            p.drawPixmap(ox, oy, scaled)
        else:
            bg = QRadialGradient(QPointF(cx, cy), inner_r)
            bg.setColorAt(0,   QColor(t.surface))
            bg.setColorAt(0.6, QColor(t.surface))
            bg.setColorAt(1,   QColor(t.bg))
            p.setBrush(QBrush(bg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawPath(donut)

            # 음표 (구멍 바깥)
            p.setClipping(False)
            p.setPen(QColor(t.accent))
            p.setFont(QFont("Malgun Gothic", 18))
            p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "♪")
            p.end()
            return

        p.setClipping(False)

        # ── 3. 구멍 (중앙 원형 컷) ──
        p.setBrush(QColor(t.bg))
        p.setPen(QPen(QColor(t.border), 1.0))
        p.drawEllipse(hole_rect)

        p.end()


# ─────────────────────────────────────────────
# 오른쪽 원 — 음파 시각화 (정적 웨이브폼 + 애니)
# ─────────────────────────────────────────────

class WaveCircle(QWidget):
    """재생 중에는 실시간 리듬 기반 음파 애니메이션 (원 없음, 8개 막대, 역동적)"""

    BAR_COUNT = 8
    # (주파수 배율, 초기 위상, 위상 증가 속도) — 제각각 움직이는 리듬감
    _BAR_PARAMS = [
        (1.7, 0.0,  0.22),
        (3.1, 0.8,  0.31),
        (2.3, 1.6,  0.18),
        (4.2, 2.4,  0.27),
        (1.5, 3.2,  0.35),
        (2.9, 4.0,  0.24),
        (3.7, 5.0,  0.29),
        (2.1, 0.4,  0.33),
    ]

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._phases = [p for _, p, _ in self._BAR_PARAMS]
        self._targets = [0.08] * self.BAR_COUNT
        self._current = [0.08] * self.BAR_COUNT
        self._active = False
        self._px: Optional[QPixmap] = None
        self.setFixedSize(68, 68)

        self._t = QTimer(self)
        self._t.timeout.connect(self._tick)
        self._t.start(16)  # ~60fps

    def set_active(self, on: bool):
        self._active = on
        if not on:
            self._targets = [0.08] * self.BAR_COUNT

    def set_pixmap(self, px: QPixmap):
        self._px = px
        self.update()

    def _tick(self):
        changed = False
        if self._active:
            for i, (freq, _, speed) in enumerate(self._BAR_PARAMS):
                self._phases[i] = (self._phases[i] + speed) % (math.pi * 2)
                # 더 극적인 움직임: 여러 파형 합산 + 하드 클리핑으로 피크 강조
                base     = abs(math.sin(self._phases[i] * freq)) ** 0.5   # 지수 낮춰서 피크 더 날카롭게
                harmonic = abs(math.sin(self._phases[i] * freq * 2.3 + 0.9)) * 0.7
                spike    = abs(math.sin(self._phases[i] * freq * 4.1 + i * 0.7)) * 0.6
                raw = (base + harmonic + spike) / 1.8
                raw = raw ** 1.6   # 비선형 강조
                self._targets[i] = 0.05 + 0.95 * min(1.0, raw)

        smooth = 0.35 if self._active else 0.25   # 기존 0.18 → 0.35
        for i in range(self.BAR_COUNT):
            diff = self._targets[i] - self._current[i]
            self._current[i] += diff * smooth
            if abs(diff) > 0.002:
                changed = True

        if self._active or changed:
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.theme
        w, h = self.width(), self.height()
        cy = h / 2

        # 배경 없음 (원 제거) — 그냥 투명
        BAR_W   = 6
        GAP     = (w - self.BAR_COUNT * BAR_W) / (self.BAR_COUNT + 1)
        max_h   = h * 0.90
        min_h   = 4
        accent_c  = QColor(t.accent)
        accent2_c = QColor(t.accent2)

        for i in range(self.BAR_COUNT):
            amp = self._current[i]
            bh  = max(min_h, int(max_h * amp))
            x   = int(GAP + i * (BAR_W + GAP))
            y1  = int(cy - bh / 2)
            y2  = int(cy + bh / 2)

            ratio = max(0.0, min(1.0, (amp - 0.08) / 0.92))
            rc = int(accent_c.red()   + (accent2_c.red()   - accent_c.red())   * ratio)
            gc = int(accent_c.green() + (accent2_c.green() - accent_c.green()) * ratio)
            bc = int(accent_c.blue()  + (accent2_c.blue()  - accent_c.blue())  * ratio)
            bar_color = QColor(max(0, min(255, rc)), max(0, min(255, gc)), max(0, min(255, bc)))

            # 막대 그라디언트
            grad = QLinearGradient(x, y1, x, y2)
            top_c = QColor(bar_color); top_c.setAlpha(255)
            bot_c = QColor(bar_color); bot_c.setAlpha(140)
            grad.setColorAt(0.0, top_c)
            grad.setColorAt(1.0, bot_c)
            pen = QPen(QBrush(grad), BAR_W, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.drawLine(x + BAR_W // 2, y1, x + BAR_W // 2, y2)

        p.end()


# ─────────────────────────────────────────────
# 흐르는 제목
# ─────────────────────────────────────────────

class MarqueeLabel(QWidget):
    """곡 제목을 ping-pong 방식으로 왕복 스크롤"""

    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._text = "재생 중인 곡 없음"
        self._offset = 0.0
        self._text_w = 0
        self._direction = 1      # 1 = 왼쪽으로, -1 = 오른쪽으로
        self._pause_ticks = 0    # 끝에서 잠깐 멈추기 위한 카운터
        self._PAUSE = 40         # 멈춤 틱 수 (~1.3초 @ 33ms)
        self.setFixedHeight(20)

        self._t = QTimer(self)
        self._t.timeout.connect(self._tick)
        self._t.start(33)

    def set_text(self, text: str):
        self._text = text
        self._offset = 0.0
        self._direction = 1
        self._pause_ticks = self._PAUSE  # 새 곡 시작 시 오른쪽 끝에서 잠깐 대기
        fm = QFontMetrics(self._font())
        self._text_w = fm.horizontalAdvance(text)
        self.update()

    def _font(self):
        return QFont("Malgun Gothic", 11, QFont.Weight.Bold)

    def _tick(self):
        overflow = self._text_w - self.width()
        if overflow <= 0:
            return  # 텍스트가 충분히 짧으면 스크롤 불필요

        if self._pause_ticks > 0:
            self._pause_ticks -= 1
            return

        self._offset += 1.1 * self._direction

        if self._direction == 1 and self._offset >= overflow:
            self._offset = overflow
            self._direction = -1
            self._pause_ticks = self._PAUSE   # 왼쪽 끝에서 멈춤
        elif self._direction == -1 and self._offset <= 0:
            self._offset = 0
            self._direction = 1
            self._pause_ticks = self._PAUSE   # 오른쪽 끝에서 멈춤

        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(self._font())
        p.setPen(QColor(self.theme.text))
        x = -self._offset if self._text_w > self.width() else 0
        p.drawText(
            QRectF(x, 0, max(self._text_w, self.width()) + 40, self.height()),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._text,
        )
        p.end()


# ─────────────────────────────────────────────
# 진행바
# ─────────────────────────────────────────────

class MiniProgressBar(QWidget):
    def __init__(self, theme: Theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self._v = 0.0
        self.setFixedHeight(3)

    def set_value(self, v: float):
        self._v = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.theme
        w, h = self.width(), self.height()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(t.border))
        p.drawRoundedRect(0, 0, w, h, 1, 1)
        fw = int(w * self._v)
        if fw > 0:
            g = QLinearGradient(0, 0, fw, 0)
            g.setColorAt(0, QColor(t.accent2))
            g.setColorAt(1, QColor(t.accent))
            p.setBrush(QBrush(g))
            p.drawRoundedRect(0, 0, fw, h, 1, 1)
        p.end()


# ─────────────────────────────────────────────
# 위젯 창
# ─────────────────────────────────────────────

class StreamWidget(QWidget):
    closed = pyqtSignal()

    def __init__(self, theme: Theme, player, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.player = player
        self._pinned = True
        self._drag_pos: Optional[QPoint] = None
        self._thumb_url = ""
        self._cur_duration = 0

        self._setup_window()
        self._build_ui()
        self._start_timer()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(340)
        self.setFixedHeight(114)
        self.resize(410, 114)

    def _build_ui(self):
        t = self.theme
        self._inner = QWidget(self)
        self._inner.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        row = QHBoxLayout(self._inner)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(12)

        # 왼쪽: 회전 디스크
        self.disk = SpinningDisk(t, self)
        row.addWidget(self.disk)

        # 중앙
        center = QVBoxLayout()
        center.setSpacing(3)
        center.setContentsMargins(0, 0, 0, 0)

        self.title_lbl  = MarqueeLabel(t, self)
        self.artist_lbl = _small_label("—", t.muted)
        self.prog_bar   = MiniProgressBar(t, self)

        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 0, 0, 0)
        self.time_cur = _small_label("0:00", t.muted, mono=True)
        self.time_tot = _small_label("0:00", t.muted, mono=True)
        time_row.addWidget(self.time_cur)
        time_row.addStretch()
        time_row.addWidget(self.time_tot)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.btn_prev  = _icon_btn(t, 22)
        self.btn_play  = _icon_btn(t, 28, accent=True)
        self.btn_next  = _icon_btn(t, 22)
        self.btn_pin   = _icon_btn(t, 22)
        self.btn_close = _icon_btn(t, 20)

        IC.set_icon(self.btn_prev,  "prev",  t.muted,       15)
        IC.set_icon(self.btn_play,  "play",  t.header_text, 17)
        IC.set_icon(self.btn_next,  "next",  t.muted,       15)
        self._refresh_pin_icon()
        IC.set_icon(self.btn_close, "close", t.muted,       12)

        btn_row.addWidget(self.btn_prev)
        btn_row.addWidget(self.btn_play)
        btn_row.addWidget(self.btn_next)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_pin)
        btn_row.addWidget(self.btn_close)

        center.addWidget(self.title_lbl)
        center.addWidget(self.artist_lbl)
        center.addWidget(self.prog_bar)
        center.addLayout(time_row)
        center.addLayout(btn_row)
        row.addLayout(center, 1)

        # 오른쪽: 음파 원
        self.wave = WaveCircle(t, self)
        row.addWidget(self.wave)

        self._inner.setLayout(row)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._inner)

        # 신호
        self.btn_play.clicked.connect(self._on_play)
        self.btn_next.clicked.connect(lambda: self.player.skip())
        self.btn_prev.clicked.connect(self._on_prev)
        self.btn_pin.clicked.connect(self._on_pin)
        self.btn_close.clicked.connect(self._on_close)

    def _refresh_pin_icon(self):
        """핀 버튼: 고정 중이면 압정(solid), 아니면 빈 압정"""
        color = self.theme.accent if self._pinned else self.theme.muted
        IC.set_icon(self.btn_pin, "pin_on" if self._pinned else "pin_off", color, 14)

    # ── 배경 페인트 ──

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.theme

        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 20, 20)

        bg = QColor(t.surface)
        bg.setAlpha(245)
        p.fillPath(path, bg)

        bar = QPainterPath()
        bar.addRoundedRect(QRectF(0, 16, 4, self.height() - 32), 2, 2)
        p.fillPath(bar, QColor(t.accent))

        p.setPen(QPen(QColor(t.accent), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.end()

    def resizeEvent(self, e):
        self._inner.setGeometry(self.rect())
        super().resizeEvent(e)

    # ── 드래그 ──

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, _):
        self._drag_pos = None

    # ── 컨트롤 ──

    def _on_play(self):
        if self.player.is_playing:
            self.player.pause()
            IC.set_icon(self.btn_play, "play",  self.theme.header_text, 17)
            self.disk.set_spinning(False)
            self.wave.set_active(False)
        elif self.player.is_paused:
            self.player.resume()
            IC.set_icon(self.btn_play, "pause", self.theme.header_text, 17)
            self.disk.set_spinning(True)
            self.wave.set_active(True)
        else:
            if self.player.queue.peek_next():
                self.player.play_next()

    def _on_prev(self):
        if self.player.queue.current:
            self.player.play_track(self.player.queue.current)

    def _on_pin(self):
        self._pinned = not self._pinned
        flags = self.windowFlags()
        if self._pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()
        self._refresh_pin_icon()

    def _on_close(self):
        self.hide()
        self.closed.emit()

    # ── 외부에서 호출 ──

    def update_track(self, track: Track):
        self.title_lbl.set_text(track.title)
        self.artist_lbl.setText(track.uploader or "—")
        self._cur_duration = track.duration
        self.time_tot.setText(track.duration_str() if track.duration else "--:--")
        IC.set_icon(self.btn_play, "pause", self.theme.header_text, 17)
        self.disk.set_spinning(True)
        self.wave.set_active(True)
        if track.thumbnail and track.thumbnail != self._thumb_url:
            self._thumb_url = track.thumbnail
            threading.Thread(target=self._load_thumb, args=(track.thumbnail,), daemon=True).start()

    def update_idle(self):
        self.title_lbl.set_text("재생 중인 곡 없음")
        self.artist_lbl.setText("—")
        IC.set_icon(self.btn_play, "play", self.theme.header_text, 17)
        self.prog_bar.set_value(0)
        self.time_cur.setText("0:00")
        self.time_tot.setText("0:00")
        self.disk.set_spinning(False)
        self.wave.set_active(False)

    def update_play_btn(self, is_playing: bool):
        icon_name = "pause" if is_playing else "play"
        IC.set_icon(self.btn_play, icon_name, self.theme.header_text, 17)
        self.disk.set_spinning(is_playing)
        self.wave.set_active(is_playing)

    def apply_theme(self, theme: Theme):
        self.theme = theme
        for w in [self.disk, self.title_lbl, self.wave, self.prog_bar]:
            w.theme = theme
        self.update()
        IC.set_icon(self.btn_prev,  "prev",  theme.muted,       15)
        IC.set_icon(self.btn_play,
                    "pause" if self.player.is_playing else "play",
                    theme.header_text, 17)
        IC.set_icon(self.btn_next,  "next",  theme.muted,       15)
        self._refresh_pin_icon()
        IC.set_icon(self.btn_close, "close", theme.muted,       12)

    def _load_thumb(self, url: str):
        try:
            data = urllib.request.urlopen(url, timeout=6).read()
            img = QImage()
            img.loadFromData(data)
            px = QPixmap.fromImage(img)
            self.disk.set_thumbnail(px)
            self.wave.set_pixmap(px)
        except Exception:
            pass

    def _start_timer(self):
        self._tick_t = QTimer(self)
        self._tick_t.timeout.connect(self._tick)
        self._tick_t.start(500)

    def _tick(self):
        if not (self.player.is_playing or self.player.is_paused):
            return
        dur = self._cur_duration or 1
        elapsed = self.player.elapsed()
        self.prog_bar.set_value(elapsed / dur)
        self.time_cur.setText(_fmt_time(int(elapsed)))


# ── 헬퍼 ──

def _small_label(text: str, color: str, mono=False):
    from PyQt6.QtWidgets import QLabel
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color:{color}; font-size:9px;"
        f"font-family:{'Consolas' if mono else 'Malgun Gothic'};"
    )
    lbl.setFixedHeight(14)
    return lbl


def _icon_btn(t: Theme, size: int = 22, accent: bool = False) -> QPushButton:
    btn = QPushButton()
    btn.setFixedSize(size, size)
    if accent:
        btn.setStyleSheet(f"""
            QPushButton {{
                background:{t.accent}; border:none; border-radius:{size//2}px;
            }}
            QPushButton:hover {{ background:{t.accent2}; }}
        """)
    else:
        btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent; border:none; border-radius:{size//2}px;
            }}
            QPushButton:hover {{ background:rgba(128,128,128,0.15); }}
        """)
    return btn