@echo off
echo.
echo  ======================================
echo   NinamamuPlayer - Nuitka Build
echo  ======================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    pause
    exit /b 1
)

python -m nuitka --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Nuitka not found. Run: pip install nuitka
    pause
    exit /b 1
)

set ICO_OPT=
set ICO_EMBED=
if exist serorong.ico (
    set ICO_OPT=--windows-icon-from-ico=serorong.ico
    set ICO_EMBED=--include-data-files=serorong.ico=cache/serorong.ico
    echo [INFO] serorong.ico found - will embed into cache/
) else (
    echo [WARN] serorong.ico not found - using default icon
)

echo [1/3] Compiling with Nuitka...
python -m nuitka ^
    --standalone ^
    --onefile ^
    --windows-console-mode=disable ^
    --enable-plugin=pyqt6 ^
    --include-package=pycaw ^
    --include-package=comtypes ^
    %ICO_OPT% ^
    %ICO_EMBED% ^
    --output-dir=dist ^
    --output-filename=NinamamuPlayer ^
    --windows-product-name="NinamamuPlayer" ^
    --windows-file-description="NinamamuPlayer" ^
    --windows-company-name="NINAMAMU" ^
    --windows-file-version="1.0.0.0" ^
    --windows-product-version="1.0.0.0" ^
    --assume-yes-for-downloads ^
    main.py

if errorlevel 1 (
    echo.
    echo [FAIL] Build error.
    pause
    exit /b 1
)

echo.
echo [2/3] Copying external tools...
set DIST=dist
for %%f in (yt-dlp.exe ffmpeg.exe ffplay.exe ffprobe.exe) do (
    if exist %%f (
        copy /Y %%f "%DIST%\" >nul
        echo   %%f copied
    ) else (
        echo   [WARN] %%f not found
    )
)

echo.
echo [3/3] Build complete!
echo.
echo  Output folder : %DIST%\
echo  Required files: NinamamuPlayer.exe, yt-dlp.exe, ffmpeg.exe, ffplay.exe, ffprobe.exe
echo.
pause