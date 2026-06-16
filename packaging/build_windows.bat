@echo off
setlocal
cd /d "%~dp0\.."
python -m PyInstaller --noconfirm --clean packaging\lantern_step.spec
if errorlevel 1 exit /b 1
echo Built dist\LanternStep\LanternStep.exe
endlocal
