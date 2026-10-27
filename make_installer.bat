@echo off
REM Batch script to build Genis executable and create installer

echo ============================================
REM Checking if virtual environment exists
if not exist .venv\Scripts\python.exe (
    echo Error: Virtual environment not found.
    echo Please run setup.ps1 first to initialize the environment.
    pause
    exit /b 1
)

REM Activating virtual environment
call .venv\Scripts\activate.bat

echo ============================================
REM Copying model to assets for embedding
echo Preparing model for embedding...
python prepare_model.py
if errorlevel 1 (
    echo Error: Failed to prepare model for embedding.
    pause
    exit /b 1
)

echo ============================================
REM Building executable with PyInstaller
echo Building executable...
pyinstaller --noconfirm --clean genis.spec
if errorlevel 1 (
    echo Error: PyInstaller build failed.
    pause
    exit /b 1
)

echo ============================================
REM Checking if build succeeded
if not exist dist\Genis\Genis.exe (
    echo Error: Executable not found at dist\Genis\Genis.exe
    pause
    exit /b 1
)

echo Build successful!
echo Size: %~zi dist\Genis\Genis.exe bytes

echo ============================================
REM Creating installer with Inno Setup (if available)
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    echo Creating installer with Inno Setup...
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
    if errorlevel 1 (
        echo Warning: Inno Setup compilation failed.
    ) else (
        echo Installer created successfully!
        echo Output: Genis-Setup.exe
    )
) else (
    echo Inno Setup not found at standard location.
    echo To create installer manually:
    echo 1. Install Inno Setup from https://jrsoftware.org/isinfo.php
    echo 2. Run: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
    echo 3. Installer will be created as Genis-Setup.exe
)

echo ============================================
echo Process completed.
pause