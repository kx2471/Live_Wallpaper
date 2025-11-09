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

echo.
echo Building executable using build.spec...
echo.

REM build.spec 파일을 사용하여 빌드 (최적화된 설정 적용)
pyinstaller --noconfirm build.spec

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
