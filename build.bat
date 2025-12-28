@echo off
echo ========================================
echo   Building Multi-AI Research Bot EXE
echo ========================================
echo.

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo Building executable...
echo.

pyinstaller --onefile --add-data "prompts;prompts" --add-data "config.example.json;." --add-data ".env.example;." --name ResearchBot main.py

echo.
echo ========================================
if exist "dist\ResearchBot.exe" (
    echo   Build successful!
    echo   Output: dist\ResearchBot.exe
) else (
    echo   Build failed. Check errors above.
)
echo ========================================
echo.
pause
