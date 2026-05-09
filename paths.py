"""
paths.py — 프로젝트 전역 기준 경로 (순환 import 없이 모든 모듈이 참조)

import 순서:
  main.py → paths.py (BASE_DIR 확정)
  updater / player / theme / ui → paths.py (이미 로드된 값 재사용)
"""

import os
import sys
from pathlib import Path


def _resolve() -> Path:
    # 1순위: Nuitka --onefile 공식 환경변수 (원본 exe 전체 경로)
    v = os.environ.get("NUITKA_ONEFILE_PARENT")
    if v:
        return Path(v).parent

    # 2순위: Nuitka 컴파일 환경 (__compiled__ 모듈이 존재)
    try:
        import __compiled__  # type: ignore[import]  # noqa: F401
        return Path(sys.argv[0]).resolve().parent
    except ImportError:
        pass

    # 3순위: 일반 .py 실행
    return Path(__file__).resolve().parent


BASE_DIR: Path = _resolve()
