@echo off
cd /d "%~dp0"
python BLR_ks.py
if errorlevel 1 (
    echo.
    echo 程序异常退出，请检查 Python 环境是否正确安装。
    pause
)
