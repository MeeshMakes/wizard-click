@echo off
setlocal
cd /d "%~dp0"

echo Launching WAV Recorder...

REM Prefer the Windows Python launcher if available.
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 audio_tool\recorder_gui.py
  exit /b %errorlevel%
)

REM Fallback to python on PATH.
where python >nul 2>nul
if %errorlevel%==0 (
  python audio_tool\recorder_gui.py
  exit /b %errorlevel%
)

echo.
echo Python was not found.
echo Install Python 3, then run: pip install -r audio_tool\requirements.txt
echo.
pause
exit /b 1
