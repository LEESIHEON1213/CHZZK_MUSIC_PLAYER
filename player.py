"""
니나마무's 플레이어 v3 — Core Engine
python-mpv + yt-dlp
- seek: 즉시 반영 (mpv 내장)
- 볼륨: 실시간 반영 (mpv 내장)
- 재생 딜레이: 최소화 (mpv가 스트리밍 직접 처리)
"""

import json
import random
import subprocess
import shutil
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Callable

import mpv

import paths


# ─────────────────────────────────────────────
# 트랙 데이터클래스
# ─────────────────────────────────────────────

@dataclass
class Track:
    title: str
    url: str
    duration: int = 0
    thumbnail: str = ""
    uploader: str = ""
    audio_url: str = ""
    source_type: str = "youtube"

    def duration_str(self) -> str:
        m, s = divmod(self.duration, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# ─────────────────────────────────────────────
# 실행파일 탐색
# ─────────────────────────────────────────────

def find_executable(name: str) -> str:
    """cache/ → exe 옆 → PATH 순으로 탐색"""
    base  = paths.BASE_DIR
    cache = base / "cache"
    import sys
    candidates = [
        cache / f"{name}.exe", cache / name,
        base  / f"{name}.exe", base  / name,
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return shutil.which(name) or name


def _ytdlp() -> str: return find_executable("yt-dlp")

_NW = subprocess.CREATE_NO_WINDOW if __import__("sys").platform == "win32" else 0


# ─────────────────────────────────────────────
# yt-dlp 유틸
# ─────────────────────────────────────────────

def run_ytdlp(args: list, timeout=30):
    try:
        r = subprocess.run(
            [_ytdlp()] + args,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout, creationflags=_NW,
        )
    except subprocess.TimeoutExpired:
        return None
    except FileNotFoundError:
        raise RuntimeError("yt-dlp.exe를 찾을 수 없습니다. 실행파일과 같은 폴더에 넣어주세요.")
    except Exception:
        return None
    if r.returncode != 0:
        return None
    out = r.stdout.strip()
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out or None


def _is_playlist_url(url: str) -> bool:
    return ("list=" in url) and ("youtube" in url or "youtu.be" in url)


def search_youtube(query: str, max_results: int = 8) -> List[Track]:
    if query.startswith("http"):
        if _is_playlist_url(query):
            return fetch_playlist(query)
        return [_url_to_track(query)]
    data = run_ytdlp(
        [f"ytsearch{max_results}:{query}", "-j",
         "--flat-playlist", "--no-warnings", "--quiet"],
        timeout=25,
    )
    if not data or not isinstance(data, str):
        return []
    tracks = []
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            t = _entry_to_track(json.loads(line))
            if t:
                tracks.append(t)
        except Exception:
            continue
    return tracks


def fetch_playlist(url: str) -> List[Track]:
    data = run_ytdlp(
        [url, "-j", "--flat-playlist", "--no-warnings", "--quiet"],
        timeout=60,
    )
    if not data or not isinstance(data, str):
        return [_url_to_track(url)]
    tracks = []
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            t = _entry_to_track(json.loads(line))
            if t:
                tracks.append(t)
        except Exception:
            continue
    return tracks if tracks else [_url_to_track(url)]


def _url_to_track(url: str) -> Track:
    data = run_ytdlp(
        [url, "-j", "--no-warnings", "--quiet",
         "--no-playlist", "--skip-download"],
        timeout=20,
    )
    if isinstance(data, dict):
        return _entry_to_track(data) or Track(title=url, url=url)
    return Track(title=url, url=url)


def _entry_to_track(obj: dict) -> Optional[Track]:
    url = obj.get("url") or obj.get("webpage_url") or obj.get("id")
    if not url:
        return None
    if not url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={url}"
    return Track(
        title=obj.get("title") or obj.get("fulltitle") or "제목 없음",
        url=url,
        duration=int(obj.get("duration") or 0),
        thumbnail=obj.get("thumbnail") or "",
        uploader=obj.get("uploader") or obj.get("channel") or "",
    )


def file_to_track(path: str) -> Track:
    name = Path(path).stem
    duration = 0
    try:
        r = subprocess.run(
            [find_executable("ffprobe"), "-v", "quiet",
             "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, creationflags=_NW,
        )
        duration = int(float(
            json.loads(r.stdout).get("format", {}).get("duration", 0)
        ))
    except Exception:
        pass
    return Track(title=name, url=path, duration=duration, source_type="file")


# ─────────────────────────────────────────────
# MPV 플레이어 엔진
# ─────────────────────────────────────────────

class MPVEngine:
    """
    python-mpv 래퍼.
    - 볼륨: mpv.volume (0~100) 실시간 반영
    - seek:  mpv.seek() 즉시 반영
    - 일시정지: mpv.pause 토글
    """

    def __init__(self):
        self._mpv: Optional[mpv.MPV] = None
        self._lock = threading.Lock()
        self._on_finish: Optional[Callable] = None
        self._volume = 30  # 기본 볼륨 30%
        self._init_mpv()

    def _init_mpv(self):
        """mpv 인스턴스 초기화"""
        try:
            m = mpv.MPV(
                ytdl=False,           # yt-dlp는 우리가 직접 처리
                video=False,          # 오디오 전용
                terminal=False,
                input_default_bindings=False,
                input_vo_keyboard=False,
            )
            m.volume = self._volume

            @m.event_callback("end-file")
            def _on_end(event):
                # reason: 0=eof, 1=stop, 2=quit, 3=error, 4=redirect, 5=unknown
                reason = event.get("reason", -1) if isinstance(event, dict) else -1
                if reason == 0:  # 정상 종료 (곡 끝)
                    cb = self._on_finish
                    if cb:
                        threading.Thread(target=cb, daemon=True).start()

            self._mpv = m
        except Exception as e:
            print(f"[MPV] 초기화 실패: {e}")
            self._mpv = None

    # ── 재생 제어 ──

    def play(self, url: str, on_finish: Optional[Callable] = None):
        """URL 재생 시작 (유튜브 URL 또는 로컬 파일 경로)"""
        with self._lock:
            self._on_finish = on_finish
            if self._mpv is None:
                self._init_mpv()
            if self._mpv:
                try:
                    self._mpv.pause = False
                    self._mpv.play(url)
                except Exception as e:
                    print(f"[MPV] 재생 실패: {e}")

    def stop(self):
        with self._lock:
            self._on_finish = None
            if self._mpv:
                try:
                    self._mpv.stop()
                except Exception:
                    pass

    def pause(self):
        with self._lock:
            if self._mpv:
                try:
                    self._mpv.pause = True
                except Exception:
                    pass

    def resume(self):
        with self._lock:
            if self._mpv:
                try:
                    self._mpv.pause = False
                except Exception:
                    pass

    def seek(self, position: float):
        """절대 위치로 seek (초 단위)"""
        with self._lock:
            if self._mpv:
                try:
                    self._mpv.seek(position, reference="absolute")
                except Exception:
                    pass

    def set_volume(self, vol: float):
        """볼륨 설정 (0.0 ~ 1.0)"""
        self._volume = int(max(0.0, min(1.0, vol)) * 100)
        with self._lock:
            if self._mpv:
                try:
                    self._mpv.volume = self._volume
                except Exception:
                    pass

    def get_volume(self) -> float:
        return self._volume / 100.0

    @property
    def elapsed(self) -> float:
        """현재 재생 위치 (초)"""
        with self._lock:
            if self._mpv:
                try:
                    pos = self._mpv.time_pos
                    return float(pos) if pos is not None else 0.0
                except Exception:
                    pass
        return 0.0

    @property
    def is_playing(self) -> bool:
        with self._lock:
            if self._mpv:
                try:
                    return not self._mpv.pause and self._mpv.time_pos is not None
                except Exception:
                    pass
        return False

    @property
    def is_paused(self) -> bool:
        with self._lock:
            if self._mpv:
                try:
                    return bool(self._mpv.pause)
                except Exception:
                    pass
        return False

    def terminate(self):
        """앱 종료 시 호출"""
        with self._lock:
            if self._mpv:
                try:
                    self._mpv.terminate()
                except Exception:
                    pass
                self._mpv = None


# ─────────────────────────────────────────────
# 재생 큐
# ─────────────────────────────────────────────

class MusicQueue:
    def __init__(self):
        self._q: List[Track] = []
        self.current: Optional[Track] = None
        self.repeat = False
        self.repeat_all = False

    def add(self, t: Track):           self._q.append(t)
    def add_many(self, ts: List[Track]): self._q.extend(ts)
    def remove(self, i: int):
        if 0 <= i < len(self._q): self._q.pop(i)
    def move(self, s: int, d: int):
        if 0 <= s < len(self._q) and 0 <= d < len(self._q):
            t = self._q.pop(s); self._q.insert(d, t)
    def shuffle(self):                 random.shuffle(self._q)
    def clear(self):                   self._q.clear()
    def pop_next(self) -> Optional[Track]:
        if not self._q: return None
        t = self._q.pop(0); self.current = t; return t
    def peek_next(self) -> Optional[Track]:
        return self._q[0] if self._q else None
    def list(self) -> List[Track]:     return list(self._q)
    def __len__(self):                 return len(self._q)


# ─────────────────────────────────────────────
# 통합 플레이어
# ─────────────────────────────────────────────

class EMAGPlayer:
    """
    MPVEngine + MusicQueue + yt-dlp 통합.
    UI는 이 클래스만 참조한다.
    """

    def __init__(self):
        self.queue   = MusicQueue()
        self._engine = MPVEngine()
        self._resolving = False
        self._resolve_lock = threading.Lock()

        # 콜백
        self.on_track_start:  Optional[Callable[[Track], None]] = None
        self.on_track_end:    Optional[Callable[[], None]]      = None
        self.on_queue_update: Optional[Callable[[], None]]      = None
        self.on_error:        Optional[Callable[[str], None]]   = None
        self.on_resolving:    Optional[Callable[[bool], None]]  = None
        self.on_thumb_update: Optional[Callable[[Track], None]] = None

    # ── 공개 API ──

    def add_and_play(self, track: Track):
        if self.is_busy:
            self.queue.add(track)
            if self.on_queue_update: self.on_queue_update()
        else:
            self._start_track(track)

    def add_many(self, tracks: List[Track]):
        if not tracks: return
        self.add_and_play(tracks[0])
        self.queue.add_many(tracks[1:])
        if self.on_queue_update: self.on_queue_update()

    def play_track(self, track: Track):
        with self._resolve_lock:
            self._resolving = False
        self._engine.stop()
        self._start_track(track)

    def play_next(self):
        with self._resolve_lock:
            if self._resolving:
                return

        if self.queue.repeat and self.queue.current:
            self._start_track(self.queue.current)
            return

        track = self.queue.pop_next()
        if not track:
            self._engine.stop()
            if self.on_track_end: self.on_track_end()
            return
        if self.queue.repeat_all:
            self.queue.add(track)
        self._start_track(track)
        if self.on_queue_update: self.on_queue_update()

    def seek(self, position: float):
        """seek — mpv가 즉시 처리, 재시작 불필요"""
        self._engine.seek(position)

    def pause(self):
        self._engine.pause()

    def resume(self):
        self._engine.resume()

    def stop(self):
        with self._resolve_lock:
            self._resolving = False
        self._engine.stop()
        self.queue.current = None

    def skip(self):
        with self._resolve_lock:
            self._resolving = False
        self._engine.stop()
        self.play_next()

    def set_volume(self, v: float):
        self._engine.set_volume(v)

    def get_volume(self) -> float:
        return self._engine.get_volume()

    def elapsed(self) -> float:
        return self._engine.elapsed

    def terminate(self):
        """앱 종료 시 반드시 호출"""
        self._engine.terminate()

    @property
    def is_playing(self) -> bool: return self._engine.is_playing
    @property
    def is_paused(self) -> bool:  return self._engine.is_paused
    @property
    def is_busy(self) -> bool:
        return self._engine.is_playing or self._engine.is_paused or self._resolving

    # ── 내부 ──

    def _start_track(self, track: Track):
        self.queue.current = track
        with self._resolve_lock:
            self._resolving = True
        if self.on_resolving: self.on_resolving(True)
        if self.on_track_start: self.on_track_start(track)
        threading.Thread(
            target=self._resolve_and_play, args=(track,), daemon=True
        ).start()

    def _resolve_and_play(self, track: Track):
        try:
            url = track.url

            # 로컬 파일은 URL 추출 없이 바로 재생
            if track.source_type == "file":
                self._play_url(track, url)
                return

            # yt-dlp로 오디오 스트림 URL + 메타데이터 추출
            data = run_ytdlp(
                [url, "-j", "--no-warnings", "--quiet",
                 "--no-playlist", "--skip-download"],
                timeout=20,
            )
            if isinstance(data, dict):
                if not track.thumbnail:
                    track.thumbnail = data.get("thumbnail") or ""
                if not track.uploader:
                    track.uploader = data.get("uploader") or data.get("channel") or ""
                if not track.duration:
                    track.duration = int(data.get("duration") or 0)
                if track.thumbnail and self.on_thumb_update:
                    self.on_thumb_update(track)

            # 오디오 스트림 URL 추출
            audio_url_raw = run_ytdlp(
                [url, "-f", "bestaudio[ext=m4a]/bestaudio/best",
                 "--get-url", "--no-playlist", "--no-warnings", "--quiet"],
                timeout=20,
            )
            if not audio_url_raw or not isinstance(audio_url_raw, str):
                raise RuntimeError(f"오디오 URL 추출 실패: {track.title[:30]}")

            audio_url = audio_url_raw.splitlines()[0].strip()
            track.audio_url = audio_url
            self._play_url(track, audio_url)

        except Exception as e:
            with self._resolve_lock:
                self._resolving = False
            if self.on_resolving: self.on_resolving(False)
            if self.on_error: self.on_error(str(e))

    def _play_url(self, track: Track, url: str):
        with self._resolve_lock:
            self._resolving = False
        if self.on_resolving: self.on_resolving(False)

        self._engine.play(url, on_finish=self.play_next)


# ─────────────────────────────────────────────
# 앱 종료 시 정리 (main.py에서 호출)
# ─────────────────────────────────────────────

def kill_all_ffmpeg():
    """하위 호환성 유지용 — v3에서는 player.terminate() 사용"""
    pass
