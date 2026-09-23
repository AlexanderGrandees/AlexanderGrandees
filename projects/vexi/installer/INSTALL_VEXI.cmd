@echo off
setlocal
echo Vexi 0.1.5.dev4 FIX10a - clean install or upgrade
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -VerifyOnly
if errorlevel 1 goto failed
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0elevate.ps1"
if errorlevel 1 goto failed
echo Installation completed. See the log for voice READY or STARTUP_PENDING.
pause
exit /b 0
:failed
echo Installation failed. See %%LOCALAPPDATA%%\VexiInstaller\install-latest.log
pause
exit /b 1
