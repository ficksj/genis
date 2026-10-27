@echo off
:loop
if exist dist\Genis\Genis.exe (
    echo.
    echo ============================================
    echo BUILD COMPLETED SUCCESSFULLY!
    echo.
    echo Genis executable created at: %CD%\dist\Genis\Genis.exe
    echo.
    echo File size: %~zi dist\Genis\Genis.exe bytes
    echo.
    echo You can now run the installer creation script:
    echo     make_installer.bat
    echo.
    goto :eof
) else (
    echo [%TIME%] Still building... (checking again in 30 seconds)
    timeout /t 30 >nul
    goto loop
)