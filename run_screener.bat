@echo off
REM =============================================================================
REM  Bottom Reversal Screener — Windows launcher
REM  Double-click this file, or run from Command Prompt.
REM =============================================================================
setlocal EnableExtensions
cd /d "%~dp0"

title Bottom Reversal Screener
echo.
echo ================================================================
echo   BOTTOM REVERSAL SCREENER - Nifty 500 + Indian ETFs
echo ================================================================
echo.

REM Prefer `py` launcher on Windows, fall back to python
where py >nul 2>&1
if %ERRORLEVEL%==0 (
  set PY=py -3
) else (
  where python >nul 2>&1
  if %ERRORLEVEL%==0 (
    set PY=python
  ) else (
    echo ERROR: Python 3 was not found on PATH.
    echo Install Python 3.10+ from https://www.python.org/downloads/
    echo IMPORTANT: check "Add Python to PATH" during install.
    pause
    exit /b 1
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo [setup] Creating virtual environment...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo Failed to create venv.
    pause
    exit /b 1
  )
)

echo [setup] Ensuring dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency install failed.
  pause
  exit /b 1
)

echo.
echo [run] Starting screener...
echo.
".venv\Scripts\python.exe" -m screener.main %*
set EXITCODE=%ERRORLEVEL%

echo.
if %EXITCODE%==0 (
  echo Finished successfully.
  echo Open the Excel file in the output\ folder.
  explorer "output"
) else (
  echo Screener exited with code %EXITCODE%.
)

echo.
pause
exit /b %EXITCODE%
