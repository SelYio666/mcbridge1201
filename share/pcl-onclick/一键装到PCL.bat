@echo off
chcp 65001 >nul
setlocal
set "HERE=%~dp0"
set "SCRIPT=%HERE%..\..\tools\from_source_install.py"
set "VER=%~1"
if "%VER%"=="" set "VER=1.21.1"

if not exist "%SCRIPT%" goto noscript

where py >nul 2>nul
if not errorlevel 1 goto use_py
where python >nul 2>nul
if not errorlevel 1 goto use_python
goto nopython

:use_py
py -3 "%SCRIPT%" --version %VER% --pcl
goto done

:use_python
python "%SCRIPT%" --version %VER% --pcl
goto done

:noscript
echo [ERROR] 找不到安装脚本: %SCRIPT%
goto done

:nopython
echo [ERROR] 没有找到 Python 3，请先安装 Python 并勾选 "Add Python to PATH"。
goto done

:done
echo.
pause
