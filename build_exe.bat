@echo off
setlocal
chcp 65001 >nul

set "BUILD_NAME=img_gen_pyqt"

REM Switch to project root (script directory)
cd /d "%~dp0"

echo [1/7] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo Please install Python 3.11+ and try again.
    pause
    exit /b 1
)

echo [2/7] Ensuring PyInstaller is installed...
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        pause
        exit /b 1
    )
)

echo [3/7] Preparing app icon...
if not exist "ui\img_icon.png" (
    echo [ERROR] Missing icon file: ui\img_icon.png
    pause
    exit /b 1
)
python -c "from PIL import Image; img=Image.open(r'ui\\img_icon.png').convert('RGBA'); img.save(r'ui\\img_icon.ico', format='ICO', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])"
if errorlevel 1 (
    echo [ERROR] Failed to generate ui\img_icon.ico from ui\img_icon.png
    echo Please ensure Pillow is available: python -m pip install pillow
    pause
    exit /b 1
)

echo [4/7] Stopping running app instances...
taskkill /f /im "%BUILD_NAME%.exe" >nul 2>&1
taskkill /f /im run.exe >nul 2>&1

echo [5/7] Cleaning old build artifacts...
if exist "build" rmdir /s /q "build" >nul 2>&1
if exist "dist\*.exe" del /f /q "dist\*.exe" >nul 2>&1

set "WORKPATH=%TEMP%\img_gen_pyqt_build_%RANDOM%_%RANDOM%"
if exist "%WORKPATH%" rmdir /s /q "%WORKPATH%" >nul 2>&1

echo [6/7] Building exe...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "%BUILD_NAME%" --icon "%cd%\ui\img_icon.ico" --add-data "ui;ui" --hidden-import src.generator --hidden-import src.processor --workpath "%WORKPATH%" run.py
if errorlevel 1 (
    echo [ERROR] Build failed.
    echo [TIP] Please close all running app windows and try again.
    pause
    exit /b 1
)

echo [6.5/7] Renaming exe to target display name...
python -c "import pathlib; src=pathlib.Path('dist')/'img_gen_pyqt.exe'; name=''.join(map(chr,[22270,20687,26174,31034,19982,26684,24335,22788,29702,24037,20855,86,49,46,49])); dst=pathlib.Path('dist')/(name + '.exe'); src.exists() or (_ for _ in ()).throw(SystemExit(f'Missing build output: {src}')); dst.exists() and dst.unlink(); src.rename(dst); print(dst)"
if errorlevel 1 (
    echo [ERROR] Failed to rename exe to target display name.
    pause
    exit /b 1
)

echo [7/7] Done.
echo Output files in dist:
dir /b "dist\*.exe"
pause
exit /b 0
