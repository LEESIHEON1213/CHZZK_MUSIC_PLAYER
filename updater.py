"""
니나마무's 플레이어 v3 — Auto Updater
yt-dlp / mpv 최신 버전 자동 체크 & 업데이트
(ffmpeg 제거 — v3는 mpv가 오디오 처리)
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


def _get_base_dir() -> Path:
    import paths as _paths
    return _paths.BASE_DIR

BASE_DIR  = _get_base_dir()
CACHE_DIR = BASE_DIR / "cache"

def _ensure_cache():
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"[updater] cache 폴더 생성 실패: {e}")

_ensure_cache()


def _tool_path(name: str) -> Path:
    if sys.platform == "win32":
        return CACHE_DIR / f"{name}.exe"
    return CACHE_DIR / name


# ─────────────────────────────────────────────
# yt-dlp 업데이트
# ─────────────────────────────────────────────

YTDLP_API  = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
YTDLP_PATH = _tool_path("yt-dlp")


def _get_ytdlp_latest() -> tuple[str, str]:
    req = urllib.request.Request(YTDLP_API, headers={"User-Agent": "NinamamuPlayer"})
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
        log(f"yt-dlp 업데이트 실패: {e}")
        return False


# ─────────────────────────────────────────────
# mpv 자동 다운로드 (Windows)
# ─────────────────────────────────────────────

MPV_API      = "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest"
MPV_PATH     = _tool_path("mpv")
MPV_VER_FILE = CACHE_DIR / ".mpv_version"


def _get_mpv_latest() -> tuple[str, str]:
    """(버전 태그, zip 다운로드 URL) 반환 — x86_64 빌드"""
    req = urllib.request.Request(MPV_API, headers={"User-Agent": "NinamamuPlayer"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    tag = data["tag_name"]
    for asset in data["assets"]:
        name = asset["name"]
        # mpv-x86_64-날짜.7z 또는 .zip 형태
        if "x86_64" in name and name.endswith(".7z") and "dev" not in name:
            return tag, asset["browser_download_url"]
    # 7z 없으면 zip 탐색
    for asset in data["assets"]:
        name = asset["name"]
        if "x86_64" in name and name.endswith(".zip") and "dev" not in name:
            return tag, asset["browser_download_url"]
    raise RuntimeError("mpv 다운로드 URL을 찾지 못했습니다.")


def _get_mpv_current() -> Optional[str]:
    if MPV_VER_FILE.exists():
        return MPV_VER_FILE.read_text().strip()
    return None


def _check_mpv_importable() -> bool:
    """python-mpv가 mpv dll을 찾을 수 있는지 확인"""
    try:
        import mpv
        m = mpv.MPV(video=False, terminal=False)
        m.terminate()
        return True
    except Exception:
        return False


def update_mpv(log: Callable[[str], None] = print) -> bool:
    """
    Windows: shinchiro mpv 빌드에서 mpv.exe + libmpv-2.dll 다운로드
    mpv.exe는 cache/에, libmpv-2.dll은 BASE_DIR(exe 옆)에 배치
    """
    if sys.platform != "win32":
        log("mpv 자동 설치는 Windows 전용입니다.")
        return False

    # 이미 python-mpv 임포트 가능하면 스킵
    if _check_mpv_importable():
        log("mpv 이미 사용 가능")
        return False

    try:
        log("mpv 버전 확인 중...")
        latest_tag, url = _get_mpv_latest()
        current = _get_mpv_current()
        if current and current == latest_tag and _check_mpv_importable():
            log(f"mpv 최신 버전 ({current})")
            return False

        log(f"mpv 다운로드 중: {latest_tag}")
        log("(수십 MB, 잠시 기다려주세요...)")

        tmp_zip = Path(tempfile.mktemp(suffix=".zip"))
        urllib.request.urlretrieve(url, tmp_zip)

        log("mpv 압축 해제 중...")
        tmp_dir = Path(tempfile.mkdtemp())

        # 7z 파일이면 7z.exe로 해제 시도, 없으면 실패 안내
        if str(url).endswith(".7z"):
            seven_zip = shutil.which("7z") or shutil.which("7za")
            if not seven_zip:
                log("7z가 없어 mpv 압축 해제 실패. 수동 설치 필요.")
                tmp_zip.unlink(missing_ok=True)
                return False
            subprocess.run(
                [seven_zip, "x", str(tmp_zip), f"-o{tmp_dir}", "-y"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            with zipfile.ZipFile(tmp_zip, "r") as zf:
                zf.extractall(tmp_dir)
        tmp_zip.unlink(missing_ok=True)

        # mpv.exe, libmpv-2.dll 찾아서 복사
        copied = []
        for p in tmp_dir.rglob("*"):
            if p.name == "mpv.exe":
                dst = CACHE_DIR / "mpv.exe"
                shutil.copy2(str(p), str(dst))
                copied.append("mpv.exe")
            elif p.name in ("libmpv-2.dll", "mpv-2.dll"):
                # dll은 exe 옆에 (python-mpv가 PATH에서 찾음)
                dst = BASE_DIR / p.name
                shutil.copy2(str(p), str(dst))
                copied.append(p.name)

        shutil.rmtree(tmp_dir, ignore_errors=True)

        if not copied:
            log("mpv 파일을 찾지 못했습니다. 수동 설치가 필요합니다.")
            return False

        MPV_VER_FILE.write_text(latest_tag)
        log(f"mpv {latest_tag} 설치 완료 ✓ ({', '.join(copied)})")
        return True

    except Exception as e:
        log(f"mpv 설치 실패: {e}")
        return False


# ─────────────────────────────────────────────
# 통합 실행
# ─────────────────────────────────────────────

def run_updates_async(
    on_log:  Callable[[str], None] = print,
    on_done: Callable[[], None]    = lambda: None,
):
    """백그라운드에서 업데이트 실행"""
    def _worker():
        update_ytdlp(on_log)
        update_mpv(on_log)
        on_done()

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t


def check_tools_exist() -> list[str]:
    """필수 도구 누락 목록 반환"""
    missing = []
    if not YTDLP_PATH.exists() and not shutil.which("yt-dlp"):
        missing.append("yt-dlp")
    if not _check_mpv_importable():
        missing.append("mpv (libmpv-2.dll)")
    return missing
