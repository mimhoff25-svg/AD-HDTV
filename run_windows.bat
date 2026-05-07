@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if exist "%SCRIPT_DIR%app.py" (
    set "ENTRYPOINT=%SCRIPT_DIR%app.py"
) else (
    echo [ERROR] Could not find app.py in "%SCRIPT_DIR%".
    echo [ERROR] Please run this launcher from the AD-HDTV repository root.
    exit /b 1
)

set "PYTHON_CMD="
where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
) else (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=python"
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python 3 was not found.
    echo [ERROR] Install Python 3.8+ from https://www.python.org/downloads/
    echo [ERROR] Then install dependencies with: py -3 -m pip install -r requirements.txt
    exit /b 1
)

%PYTHON_CMD% "%ENTRYPOINT%" %*
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
    echo.
    echo [ERROR] AD-HDTV exited with code %EXIT_CODE%.
    echo [ERROR] If this is a dependency issue, run: %PYTHON_CMD% -m pip install -r requirements.txt
    echo [ERROR] Ensure VLC is installed from https://www.videolan.org/vlc/
)
exit /b %EXIT_CODE%
