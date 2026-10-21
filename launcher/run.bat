@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"

if not defined PY (
  echo.
  echo 未找到 Python，请先安装 Python 3.10 或更高版本。
  echo 下载： https://www.python.org/downloads/
  echo.
  pause
  exit /b 1
)

echo 正在启动 mcbridge launcher ...
echo 浏览器会自动打开 http://127.0.0.1:8765/  关闭本窗口即停止启动器。
echo.
%PY% server.py
pause
