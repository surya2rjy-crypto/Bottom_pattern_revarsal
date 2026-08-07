@echo off
REM Quick smoke test (first 40 symbols) — useful to verify install
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  call run_screener.bat --limit 40
  exit /b %ERRORLEVEL%
)
".venv\Scripts\python.exe" -m screener.main --limit 40 %*
pause
