@echo off
setlocal EnableExtensions
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%" >nul
set "SCRIPT_DIR=%CD%\"

where py.exe >nul 2>nul
if not errorlevel 1 goto use_py_launcher

where python.exe >nul 2>nul
if not errorlevel 1 goto use_python

goto no_python

:use_py_launcher
py.exe -3 "%SCRIPT_DIR%split_audio.py" %*
goto end

:use_python
python.exe "%SCRIPT_DIR%split_audio.py" %*
goto end

:no_python
echo Python 3 was not found.
echo Please install Python 3, then run this file again.
echo See README.md for the steps.

:end
echo.
pause
popd >nul
endlocal
