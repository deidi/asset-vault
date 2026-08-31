@echo off
setlocal
cd /d "%~dp0"
echo Starting AssetVault Desktop Application...
.\backend\.venv\Scripts\python.exe desktop_app.py
endlocal
