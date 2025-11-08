@echo off
echo ================================================
echo Windows Live Wallpaper Player - Build Script
echo ================================================
echo.

REM 이전 빌드 정리
if exist "build" (
    echo Cleaning previous build folder...
    rmdir /s /q build
)
if exist "dist" (
    echo Cleaning previous dist folder...
    rmdir /s /q dist
)
if exist "WallpaperPlayer.spec" (
    echo Cleaning previous spec file...
    del WallpaperPlayer.spec
)

echo.
echo Building executable...
echo.

REM PyInstaller로 실행 파일 생성
pyinstaller --onefile ^
    --windowed ^
    --name="WallpaperPlayer" ^
    --add-data="icon;icon" ^
    --hidden-import=pygame ^
    --hidden-import=cv2 ^
    --hidden-import=moviepy.editor ^
    --hidden-import=win32gui ^
    --hidden-import=win32con ^
    --hidden-import=win32api ^
    --hidden-import=tkinter ^
    --collect-all moviepy ^
    --copy-metadata imageio ^
    --copy-metadata imageio-ffmpeg ^
    --copy-metadata proglog ^
    --copy-metadata decorator ^
    --copy-metadata tqdm ^
    --exclude-module torch ^
    --exclude-module pandas ^
    --exclude-module scipy ^
    --exclude-module matplotlib ^
    --exclude-module pytest ^
    --exclude-module IPython ^
    --exclude-module jinja2 ^
    --exclude-module sympy ^
    --exclude-module pyarrow ^
    --exclude-module test ^
    --exclude-module tests ^
    --noconfirm ^
    main.py

if %errorlevel% equ 0 (
    echo.
    echo ================================================
    echo Build completed successfully!
    echo Executable: dist\WallpaperPlayer.exe
    echo ================================================
) else (
    echo.
    echo ================================================
    echo Build failed! Please check the errors above.
    echo ================================================
)

echo.
pause
