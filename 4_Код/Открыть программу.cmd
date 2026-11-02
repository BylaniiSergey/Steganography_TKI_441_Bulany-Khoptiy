@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "LAB_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%LAB_PYTHON%" (
  "%LAB_PYTHON%" src\app.py
) else (
  py src\app.py
)
if errorlevel 1 pause
