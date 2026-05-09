"""
EMAG Player - Auto Updater
매 실행 시 yt-dlp / ffmpeg 최신 버전 자동 체크 & 업데이트
도구는 exe 옆 cache/ 폴더에 저장 — 매 실행 시 재다운로드 없음
"""

import os
import sys
import json
import shutil
import zipfile
import tempfile
import threading
import subprocess
import urllib.request
from pathlib import Path
from typing import Callable, Optional


# ─────────────────────────────────────────────
# 경로 기준: 실행파일 옆 cache/ 폴더
# ─────────────────────────────────────────────

def _get_base_dir() -> Path:
    import paths as _paths
    return _paths.BASE_DIR

BASE_DIR = _get_base_dir()

# 도구는 항상 cache/ 하위에 저장
CACHE_DIR = BASE_DIR / "cache"

def _ensure_cache():
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[updater] cache 폴더 생성 실패: {CACHE_DIR} — {e}")

_ensure_cache()


def _tool_path(name: str) -> Path:
    """cache/ 안의 바이너리 경로 반환"""
    if sys.platform == "win32":
        return CACHE_DIR / f"{name}.exe"
    return CACHE_DIR / name


# ─────────────────────────────────────────────
# yt-dlp 업데이트
# ─────────────────────────────────────────────

YTDLP_API  = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
YTDLP_PATH = _tool_path("yt-dlp")


def _get_ytdlp_latest() -> tuple[str, str]:
    """(버전 태그, 다운로드 URL) 반환"""
    req = urllib.request.Request(YTDLP_API, headers={"User-Agent": "EMAG-Player"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    tag = data["tag_name"]
    asset_name = "yt-dlp.exe" if sys.platform == "win32" else "yt-dlp"
    for asset in data["assets"]:
        if asset["name"] == asset_name:
            return tag, asset["browser_download_url"]
    raise RuntimeError("yt-dlp 다운로드 URL을 찾지 못했습니다.")


def _get_ytdlp_current() -> Optional[str]:
    if not YTDLP_PATH.exists():
        return None
    try:
        r = subprocess.run(
            [str(YTDLP_PATH), "--version"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return r.stdout.strip()
    except Exception:
        return None


def update_ytdlp(log: Callable[[str], None] = print) -> bool:
    """최신 버전이면 True, 업데이트 필요 없으면 False"""
    try:
        log("yt-dlp 버전 확인 중...")
        latest_tag, url = _get_ytdlp_latest()
        current = _get_ytdlp_current()
        if current and current == latest_tag:
            log(f"yt-dlp 최신 버전 ({current})")
            return False
        log(f"yt-dlp 업데이트: {current or '없음'} → {latest_tag}")
        tmp = Path(tempfile.mktemp(suffix=".exe" if sys.platform == "win32" else ""))
        urllib.request.urlretrieve(url, tmp)
        shutil.move(str(tmp), str(YTDLP_PATH))
        if sys.platform != "win32":
            os.chmod(YTDLP_PATH, 0o755)
        log(f"yt-dlp {latest_tag} 업데이트 완료 ✓")
        return True
    except Exception as e:
        log(f"yt-dlp 업데이트 실패 (네트워크 문제?): {e}")
        return False


# ─────────────────────────────────────────────
# ffmpeg 업데이트 (Windows: gyan.dev 빌드)
# ─────────────────────────────────────────────

FFMPEG_VERSION_URL = "https://www.gyan.dev/ffmpeg/builds/release-version"
FFMPEG_ZIP_URL     = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
FFMPEG_PATH  = _tool_path("ffmpeg")
FFPLAY_PATH  = _tool_path("ffplay")
FFPROBE_PATH = _tool_path("ffprobe")
FFMPEG_VER_FILE = CACHE_DIR / ".ffmpeg_version"


def _get_ffmpeg_latest_tag() -> str:
    req = urllib.request.Request(FFMPEG_VERSION_URL, headers={"User-Agent": "EMAG-Player"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode().strip()


def _get_ffmpeg_current() -> Optional[str]:
    if FFMPEG_VER_FILE.exists():
        return FFMPEG_VER_FILE.read_text().strip()
    if not FFMPEG_PATH.exists():
        return None
    try:
        r = subprocess.run(
            [str(FFMPEG_PATH), "-version"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        for line in r.stdout.splitlines():
            if "ffmpeg version" in line:
                return line.split()[2]
    except Exception:
        pass
    return None


def update_ffmpeg(log: Callable[[str], None] = print) -> bool:
    if sys.platform != "win32":
        log("ffmpeg 자동업데이트는 Windows 전용입니다. (Linux/Mac은 패키지 매니저 사용)")
        return False
    try:
        log("ffmpeg 버전 확인 중...")
        latest = _get_ffmpeg_latest_tag()
        current = _get_ffmpeg_current()
        if current and current == latest:
            log(f"ffmpeg 최신 버전 ({current})")
            return False
        log(f"ffmpeg 업데이트: {current or '없음'} → {latest}")
        log("ffmpeg 다운로드 중... (수십 MB, 잠시 기다려주세요)")

        tmp_zip = Path(tempfile.mktemp(suffix=".zip"))
        urllib.request.urlretrieve(FFMPEG_ZIP_URL, tmp_zip)

        log("ffmpeg 압축 해제 중...")
        tmp_dir = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(tmp_zip, "r") as zf:
            zf.extractall(tmp_dir)
        tmp_zip.unlink(missing_ok=True)

        # zip 내부 구조: ffmpeg-X.X-essentials_build/bin/*.exe
        bin_dir = None
        for p in tmp_dir.rglob("bin"):
            if p.is_dir():
                bin_dir = p
                break

        if not bin_dir:
            log("ffmpeg 압축 구조를 인식하지 못했습니다.")
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return False

        for exe_name in ("ffmpeg.exe", "ffplay.exe", "ffprobe.exe"):
            src = bin_dir / exe_name
            dst = CACHE_DIR / exe_name   # cache/ 에 저장
            if src.exists():
                shutil.copy2(str(src), str(dst))

        shutil.rmtree(tmp_dir, ignore_errors=True)
        FFMPEG_VER_FILE.write_text(latest)
        log(f"ffmpeg {latest} 업데이트 완료 ✓")
        return True
    except Exception as e:
        log(f"ffmpeg 업데이트 실패: {e}")
        return False


# ─────────────────────────────────────────────
# 통합 실행 (백그라운드 스레드)
# ─────────────────────────────────────────────

def run_updates_async(on_log: Callable[[str], None] = print,
                      on_done: Callable[[], None] = lambda: None):
    """백그라운드에서 업데이트 실행, UI 블로킹 없음"""
    def _worker():
        update_ytdlp(on_log)
        update_ffmpeg(on_log)
        on_done()

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t


def check_tools_exist() -> list[str]:
    """필수 도구 누락 목록 반환 (cache/ 우선 확인)"""
    missing = []
    if not YTDLP_PATH.exists() and not shutil.which("yt-dlp"):
        missing.append("yt-dlp")
    if not FFPLAY_PATH.exists() and not shutil.which("ffplay"):
        missing.append("ffplay (ffmpeg 패키지에 포함)")
    return missing