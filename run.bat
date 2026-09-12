@echo off
chcp 65001 >nul
title 进程网络限速助手 - 启动器
echo ======================================================
echo           进程网络限速助手 (ProcessNetLimiter)
echo ======================================================
echo 正在检查管理员权限...

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 检测到非管理员模式。
    echo 正在为您请求管理员权限 (UAC)...
    powershell -Command "Start-Process python -ArgumentList 'main.py' -Verb RunAs"
    exit /b
)

echo [OK] 已具备管理员权限，正在启动主程序...
python main.py
if %errorlevel% neq 0 (
    echo.
    echo 程序退出或发生错误，按任意键关闭窗口...
    pause >nul
)
