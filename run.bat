@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 进程网络限速助手 (ProcessNetLimiter)

echo ======================================================
echo           进程网络限速助手 (ProcessNetLimiter)
echo ======================================================

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请确认已正确安装 Python 并配置环境变量。
    echo.
    pause
    exit /b 1
)

echo 正在启动主程序，请稍候...
python main.py

if %errorlevel% neq 0 (
    echo.
    echo ======================================================
    echo [提示] 程序已退出 (退出代码: %errorlevel%)。
    echo ======================================================
    pause
)
