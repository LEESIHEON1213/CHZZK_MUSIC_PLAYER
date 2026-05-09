"""
니나마무's 플레이어 — Core Engine
yt-dlp + ffplay + 볼륨 / seek / 플레이리스트 지원
"""

import os, sys, json, time, threading, subprocess, shutil, random
from dataclasses import dataclass
from typing import Optional, List, Callable
from pathlib import Path


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


def _set_process_volume(pid: int, volume: float) -> bool:
    """Windows Audio Session API(pycaw)로 특정 PID의 세션 볼륨을 실시간 조절."""
    if sys.platform != "win32":
        return False
    try:
        from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume
        sessions = AudioUtilities.GetAllSessions()
        for session in sessions:
            if session.Process and session.Process.pid == pid:
                volume_interface = session._ctl.QueryInterface(ISimpleAudioVolume)
                volume_interface.SetMasterVolume(max(0.0, min(1.0, volume)), None)
                return True
    except Exception:
        pass
    return False


def _get_base_dir() -> Path:
    import paths as _paths
    return _paths.BASE_DIR


def find_executable(name: str) -> str:
    base = _get_base_dir()
    cache = base / "cache"
    # cache/ 우선 탐색, 그 다음 exe 옆, 마지막으로 PATH
    candidates = [
        cache / f"{name}.exe", cache / name,
        base  / f"{name}.exe", base  / name,
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return shutil.which(name) or name


# 실행 시마다 동적으로 탐색 (onefile exe에서 cache/ 경로 보장)
def _ytdlp()   -> str: return find_executable("yt-dlp")
def _ffplay()  -> str: return find_executable("ffplay")
def _ffprobe() -> str: return find_executable("ffprobe")

_NW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


# ─────────────────────────────────────────────
# 전역 프로세스 추적 — 창 닫을 때 모두 종료
# ─────────────────────────────────────────────

_ALL_PROCS: List = []
_PROCS_LOCK = threading.Lock()


def _register_proc(proc):
    with _PROCS_LOCK:
        _ALL_PROCS.append(proc)


def _unregister_proc(proc):
    with _PROCS_LOCK:
        try:
            _ALL_PROCS.remove(proc)
        except ValueError:
            pass


def kill_all_ffmpeg():
    """창 종료 시 호출 — ffplay/yt-dlp 프로세스 전부 강제 종료"""
    with _PROCS_LOCK:
        procs = list(_ALL_PROCS)
        _ALL_PROCS.clear()

    # 1단계: 등록된 프로세스 즉시 강제 종료
    for p in procs:
        try:
            if p.poll() is None:
                p.kill()
        except Exception:
            pass

    # 2단계: Windows — 프로세스 트리 포함 강제 종료 (/T = 자식까지)
    if sys.platform == "win32":
        for p in procs:
            try:
                if p.pid:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                        creationflags=_NW,
                        capture_output=True,
                        timeout=3,
                    )
            except Exception:
                pass
        # 3단계: 이름 기반 전체 스캔 (고아 프로세스 정리)
        for name in ("ffplay.exe", "ffmpeg.exe", "yt-dlp.exe"):
            try:
                subprocess.run(
                    ["taskkill", "/F", "/IM", name],
                    creationflags=_NW,
                    capture_output=True,
                    timeout=3,
                )
            except Exception:
                pass
    else:
        # Linux/Mac: SIGKILL
        import signal as _sig
        for p in procs:
            try:
                if p.poll() is None:
                    p.send_signal(_sig.SIGKILL)
            except Exception:
                pass


# ─────────────────────────────────────────────
# yt-dlp
# ─────────────────────────────────────────────

def run_ytdlp(args: list, timeout=30):
    try:
        r = subprocess.run(
            [_ytdlp()] + args, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, creationflags=_NW,
        )
    except subprocess.TimeoutExpired:
        return None
    except FileNotFoundError:
        raise RuntimeError("yt-dlp.exe를 실행파일과 같은 폴더에 넣어주세요.")
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


def search_youtube(query: str, max_results: int = 8) -> List["Track"]:
    if query.startswith("http"):
        if _is_playlist_url(query):
            return fetch_playlist(query)
        return [_url_to_track(query)]
    data = run_ytdlp([f"ytsearch{max_results}:{query}", "-j",
                      "--flat-playlist", "--no-warnings", "--quiet"], timeout=25)
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


def fetch_playlist(url: str) -> List["Track"]:
    """플레이리스트 URL에서 모든 곡 flat 추출"""
    data = run_ytdlp([
        url, "-j", "--flat-playlist", "--no-warnings", "--quiet",
    ], timeout=60)
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


def _url_to_track(url: str) -> "Track":
    data = run_ytdlp([url, "-j", "--no-warnings", "--quiet",
                      "--no-playlist", "--skip-download"], timeout=20)
    if isinstance(data, dict):
        return _entry_to_track(data) or Track(title=url, url=url)
    return Track(title=url, url=url)


def _entry_to_track(obj: dict) -> Optional["Track"]:
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


# ─────────────────────────────────────────────
# ffplay 재생 엔진
# ─────────────────────────────────────────────

class FFmpegPlayer:
    def __init__(self):
        self._proc = None
        self._ytdlp_proc = None
        self._lock = threading.Lock()
        self._play_id = 0
        self._finish_id = 0
        self.is_playing = False
        self.is_paused = False
        self._volume = 0.8

    def play(self, audio_url: str, on_finish=None, seek_to: float = 0.0):
        self.stop()
        with self._lock:
            self._play_id += 1
            my_id = self._play_id
        self.is_playing = True
        threading.Thread(
            target=self._run, args=(audio_url, my_id, on_finish, seek_to), daemon=True
        ).start()

    def stop(self):
        with self._lock:
            self._play_id += 1
            self._finish_id += 1
            proc, self._proc = self._proc, None
            yp, self._ytdlp_proc = self._ytdlp_proc, None
        for p in [proc, yp]:
            if p and p.poll() is None:
                try:
                    p.kill()
                    p.wait(timeout=1)
                except Exception:
                    try: p.kill()
                    except Exception: pass
                _unregister_proc(p)
        self.is_playing = False
        self.is_paused = False

    def pause(self):
        if not self.is_playing or self.is_paused:
            return
        self.is_paused = True
        self.is_playing = False
        self._signal("suspend")

    def resume(self):
        if not self.is_paused:
            return
        self.is_paused = False
        self.is_playing = True
        self._signal("resume")

    def set_volume(self, vol: float):
        """볼륨 변경 — Windows: Audio Session API로 ffplay 프로세스 볼륨 실시간 조절"""
        self._volume = max(0.0, min(1.0, vol))
        with self._lock:
            proc = self._proc
        if proc and proc.poll() is None:
            _set_process_volume(proc.pid, self._volume)

    def get_volume(self) -> float:
        return self._volume

    def _run(self, audio_url: str, play_id: int, on_finish, seek_to: float = 0.0):
        use_pipe = ("googlevideo.com" in audio_url or
                    "youtube.com" in audio_url or
                    "youtu.be" in audio_url)

        returncode = -1
        ytdlp_proc = None
        try:
            ffplay_vol = self._volume * 1.5  # 0~1 → 0~1.5

            if use_pipe:
                ytdlp_cmd = [
                    _ytdlp(), "-f", "bestaudio/best",
                    "--no-playlist", "-o", "-", "--quiet", audio_url,
                ]
                ffplay_cmd = [
                    _ffplay(), "-nodisp", "-autoexit",
                    "-hide_banner", "-loglevel", "quiet",
                    "-af", f"volume={ffplay_vol:.4f}",
                ]
                if seek_to > 1.0:
                    ffplay_cmd += ["-ss", f"{seek_to:.1f}"]
                ffplay_cmd += ["-"]

                ytdlp_proc = subprocess.Popen(
                    ytdlp_cmd, creationflags=_NW,
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                )
                _register_proc(ytdlp_proc)
                proc = subprocess.Popen(
                    ffplay_cmd, creationflags=_NW,
                    stdin=ytdlp_proc.stdout,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                _register_proc(proc)
                ytdlp_proc.stdout.close()
            else:
                cmd = [
                    _ffplay(), "-nodisp", "-autoexit",
                    "-hide_banner", "-loglevel", "quiet",
                    "-af", f"volume={ffplay_vol:.4f}",
                ]
                if seek_to > 1.0:
                    cmd += ["-ss", f"{seek_to:.1f}"]
                cmd += [audio_url]
                proc = subprocess.Popen(
                    cmd, creationflags=_NW,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                _register_proc(proc)
                ytdlp_proc = None

            with self._lock:
                if self._play_id != play_id:
                    proc.terminate()
                    _unregister_proc(proc)
                    if ytdlp_proc:
                        try: ytdlp_proc.terminate()
                        except Exception: pass
                        _unregister_proc(ytdlp_proc)
                    return
                self._proc = proc
                self._ytdlp_proc = ytdlp_proc

            # ffplay 시작 직후 pycaw로 볼륨 세션 적용 (약간의 딜레이 필요)
            def _apply_vol_after_start():
                import time as _t
                _t.sleep(0.5)
                _set_process_volume(proc.pid, self._volume)
            threading.Thread(target=_apply_vol_after_start, daemon=True).start()

            proc.wait()
            # 타임아웃 루프: 100ms마다 종료 확인, play_id 바뀌면 즉시 탈출
            while True:
                try:
                    proc.wait(timeout=0.1)
                    break
                except subprocess.TimeoutExpired:
                    with self._lock:
                        if self._play_id != play_id:
                            break
            returncode = proc.returncode
            _unregister_proc(proc)

            if ytdlp_proc:
                try:
                    ytdlp_proc.wait(timeout=2)
                except Exception:
                    try: ytdlp_proc.kill()
                    except Exception: pass
                _unregister_proc(ytdlp_proc)

        except FileNotFoundError:
            pass
        except Exception:
            pass
        finally:
            self.is_playing = False

        with self._lock:
            still_mine  = (self._play_id == play_id)
            finish_snap = self._finish_id

        if returncode == 0 and still_mine and on_finish:
            on_finish(finish_snap)

    def _signal(self, action: str):
        with self._lock:
            proc = self._proc
        if not proc:
            return
        try:
            if sys.platform == "win32":
                import ctypes
                h = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, proc.pid)
                (ctypes.windll.ntdll.NtSuspendProcess if action == "suspend"
                 else ctypes.windll.ntdll.NtResumeProcess)(h)
                ctypes.windll.kernel32.CloseHandle(h)
            else:
                import signal as _sig
                proc.send_signal(_sig.SIGSTOP if action == "suspend" else _sig.SIGCONT)
        except Exception:
            pass


# ─────────────────────────────────────────────
# 큐
# ─────────────────────────────────────────────

class MusicQueue:
    def __init__(self):
        self._q: List[Track] = []
        self.current: Optional[Track] = None
        self.repeat = False
        self.repeat_all = False

    def add(self, t: Track): self._q.append(t)
    def add_many(self, ts: List[Track]): self._q.extend(ts)
    def remove(self, i: int):
        if 0 <= i < len(self._q): self._q.pop(i)
    def move(self, s: int, d: int):
        if 0 <= s < len(self._q) and 0 <= d < len(self._q):
            t = self._q.pop(s); self._q.insert(d, t)
    def shuffle(self): random.shuffle(self._q)
    def clear(self): self._q.clear()
    def pop_next(self) -> Optional[Track]:
        if not self._q: return None
        t = self._q.pop(0); self.current = t; return t
    def peek_next(self) -> Optional[Track]:
        return self._q[0] if self._q else None
    def list(self) -> List[Track]: return list(self._q)
    def __len__(self): return len(self._q)


# ─────────────────────────────────────────────
# 통합 플레이어
# ─────────────────────────────────────────────

class EMAGPlayer:
    def __init__(self):
        self.queue = MusicQueue()
        self._engine = FFmpegPlayer()
        self._current_start = 0.0
        self._elapsed_offset = 0.0
        self._resolving = False
        self._resolve_lock = threading.Lock()
        self._current_audio_url: Optional[str] = None

        self.on_track_start:  Optional[Callable] = None
        self.on_track_end:    Optional[Callable] = None
        self.on_queue_update: Optional[Callable] = None
        self.on_error:        Optional[Callable] = None
        self.on_resolving:    Optional[Callable] = None
        self.on_thumb_update: Optional[Callable] = None

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

    def play_next(self, finish_id: int = -1):
        if finish_id >= 0:
            with self._engine._lock:
                if self._engine._finish_id != finish_id:
                    return

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
        """재생 시점 이동 (초 단위)"""
        track = self.queue.current
        if not track:
            return
        audio_url = self._current_audio_url or track.url
        self._elapsed_offset = position
        self._current_start = time.time()

        was_playing = self._engine.is_playing or self._engine.is_paused
        self._engine.stop()
        if was_playing:
            self._engine.is_playing = True
            with self._engine._lock:
                self._engine._play_id += 1
                my_id = self._engine._play_id
            threading.Thread(
                target=self._engine._run,
                args=(audio_url, my_id,
                      lambda fid: self.play_next(finish_id=fid),
                      position),
                daemon=True,
            ).start()

    def pause(self):
        if not self._engine.is_playing:
            return
        self._elapsed_offset += time.time() - self._current_start
        self._engine.pause()

    def resume(self):
        if not self._engine.is_paused:
            return
        self._current_start = time.time()
        self._engine.resume()

    def stop(self):
        with self._resolve_lock:
            self._resolving = False
        self._engine.stop()
        self.queue.current = None
        self._current_audio_url = None

    def skip(self):
        with self._resolve_lock:
            self._resolving = False
        self._engine.stop()
        self.play_next(finish_id=-1)

    def set_volume(self, v: float):
        """볼륨 변경 — pycaw Audio Session API로 ffplay 프로세스 볼륨 실시간 조절"""
        self._engine.set_volume(v)

    def elapsed(self) -> float:
        if self._engine.is_playing:
            return self._elapsed_offset + (time.time() - self._current_start)
        return self._elapsed_offset

    @property
    def is_playing(self) -> bool: return self._engine.is_playing
    @property
    def is_paused(self) -> bool: return self._engine.is_paused
    @property
    def is_busy(self) -> bool:
        return self._engine.is_playing or self._engine.is_paused or self._resolving

    def _start_track(self, track: Track):
        self.queue.current = track
        self._elapsed_offset = 0.0
        self._current_start = time.time()
        self._current_audio_url = None
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

            # 썸네일이 없는 경우(flat-playlist 등) 메타데이터 보충
            if not track.thumbnail and url.startswith("http"):
                try:
                    data = run_ytdlp([url, "-j", "--no-warnings", "--quiet",
                                      "--no-playlist", "--skip-download"], timeout=15)
                    if isinstance(data, dict):
                        if not track.thumbnail:
                            track.thumbnail = data.get("thumbnail") or ""
                        if not track.uploader:
                            track.uploader = data.get("uploader") or data.get("channel") or ""
                        if not track.duration:
                            track.duration = int(data.get("duration") or 0)
                        # 썸네일 갱신됐으면 on_thumb_update로 위젯 썸네일만 업데이트
                        if track.thumbnail and self.on_thumb_update:
                            self.on_thumb_update(track)
                except Exception:
                    pass

            self._current_audio_url = url

            with self._resolve_lock:
                self._resolving = False
            if self.on_resolving: self.on_resolving(False)

            if not url:
                if self.on_error: self.on_error(f"재생 URL 없음: {track.title[:30]}")
                self.play_next()
                return

            track.audio_url = url
            self._engine.play(url, on_finish=lambda fid: self.play_next(finish_id=fid))

        except Exception as e:
            with self._resolve_lock:
                self._resolving = False
            if self.on_resolving: self.on_resolving(False)
            if self.on_error: self.on_error(str(e))


def file_to_track(path: str) -> Track:
    name = Path(path).stem
    duration = 0
    try:
        r = subprocess.run(
            [_ffprobe(), "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, creationflags=_NW,
        )
        duration = int(float(json.loads(r.stdout).get("format", {}).get("duration", 0)))
    except Exception:
        pass
    return Track(title=name, url=path, duration=duration, source_type="file")