# -*- coding: utf-8 -*-
"""
高权限开机自启任务管理模块 (autostart_manager)
针对 Windows UAC 高权限软件设计：
- 普通注册表 Run 项在开机加载管理员权限应用时会被 Windows UAC 静默拦截或报错；
- 采用工业级标准方案：利用 Windows 任务计划程序 (Task Scheduler, schtasks.exe)；
- 配置 `RunLevel=HighestAvailable` 与 `/sc onlogon`，实现开机登录时免弹窗静默启动，并附带 `--minimized` 参数。
"""
import sys
import os
import subprocess

TASK_NAME = "ProcessNetLimiterAutoStart"
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def _get_app_startup_command() -> str:
    """获取启动本程序的完整命令行路径（支持 PyInstaller 单文件打包模式与源码运行模式）"""
    if getattr(sys, "frozen", False):
        exe_path = os.path.abspath(sys.executable)
        return f'"{exe_path}" --minimized'
    else:
        # 源码运行模式：优先寻找无控制台黑框的 pythonw.exe
        python_dir = os.path.dirname(sys.executable)
        pythonw_path = os.path.join(python_dir, "pythonw.exe")
        py_exe = pythonw_path if os.path.exists(pythonw_path) else sys.executable

        main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
        main_py = os.path.normpath(main_py)
        return f'"{py_exe}" "{main_py}" --minimized'


def is_autostart_enabled() -> bool:
    """检查是否已经注册了开机启动计划任务"""
    if sys.platform != "win32":
        return False
    try:
        cmd = ["schtasks", "/query", "/tn", TASK_NAME]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW,
            timeout=5
        )
        return res.returncode == 0
    except Exception:
        return False


def set_autostart(enable: bool) -> tuple[bool, str]:
    """启用或禁用开机静默启动"""
    if sys.platform != "win32":
        return False, "Only supported on Windows"

    if enable:
        start_cmd = _get_app_startup_command()
        # 创建计划任务：开机登录执行，最高权限，强制覆盖
        cmd = [
            "schtasks", "/create",
            "/tn", TASK_NAME,
            "/tr", start_cmd,
            "/sc", "onlogon",
            "/rl", "highest",
            "/f"
        ]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                timeout=10
            )
            if res.returncode == 0:
                return True, "Success"
            else:
                err = (res.stderr or res.stdout or "").strip()
                return False, f"schtasks failed: {err}"
        except Exception as e:
            return False, f"Execution error: {e}"
    else:
        cmd = ["schtasks", "/delete", "/tn", TASK_NAME, "/f"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=CREATE_NO_WINDOW,
                timeout=10
            )
            if res.returncode == 0 or "cannot find" in (res.stderr or "").lower():
                return True, "Success"
            else:
                err = (res.stderr or res.stdout or "").strip()
                return False, f"schtasks failed: {err}"
        except Exception as e:
            return False, f"Execution error: {e}"
