"""
니나마무's 플레이어 — 진입점
"""

import sys
import atexit
import json
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QFont

# paths 를 가장 먼저 import → BASE_DIR 확정
import paths  # noqa: F401  (다른 모듈들이 paths.BASE_DIR 을 참조)

from updater import check_tools_exist
from player import kill_all_ffmpeg
from ui import MainWindow

APP_NAME = "니나마무's 플레이어"

_DEFAULT_FILES: dict[str, str] = {
    "favorites.json": json.dumps([], ensure_ascii=False, indent=2),
    "theme.json":     json.dumps({"name": "니나마무"}, ensure_ascii=False, indent=2),
    ".ffmpeg_version": "",
}


def ensure_default_files() -> None:
    """없는 기본 파일만 자동 생성 (기존 파일 절대 덮어쓰지 않음)."""
    for filename, default_content in _DEFAULT_FILES.items():
        path = paths.BASE_DIR / filename
        if not path.exists():
            try:
                path.write_text(default_content, encoding="utf-8")
            except Exception as e:
                print(f"[main] {filename} 생성 실패: {e}")


def main():
    ensure_default_files()

    atexit.register(kill_all_ffmpeg)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setFont(QFont("Malgun Gothic", 10))
    app.aboutToQuit.connect(kill_all_ffmpeg)

    missing = check_tools_exist()
    if missing:
        msg = QMessageBox()
        msg.setWindowTitle("도구 누락")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(
            "다음 도구가 실행파일 폴더에 없습니다:\n\n"
            + "\n".join(f"  • {m}" for m in missing)
            + "\n\n계속 진행하면 검색/재생이 작동하지 않을 수 있습니다."
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
        )
        if msg.exec() == QMessageBox.StandardButton.Cancel:
            sys.exit(0)

    window = MainWindow()
    import signal as _signal
    _signal.signal(_signal.SIGTERM, lambda *_: (kill_all_ffmpeg(), sys.exit(0)))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
