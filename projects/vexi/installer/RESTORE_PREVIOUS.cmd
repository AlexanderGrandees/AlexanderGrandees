@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0elevate.ps1" -Restore
if errorlevel 1 goto failed
echo Previous installation restored.
pause
exit /b 0
:failed
echo Restore failed. See the installer log.
pause
exit /b 1
