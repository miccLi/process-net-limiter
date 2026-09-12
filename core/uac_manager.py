# -*- coding: utf-8 -*-
"""
UAC 权限管理模块
检测当前是否以管理员权限运行，以及提供便捷的 UAC 提权重启和提权执行功能。
"""
import sys
import os
import ctypes
import subprocess
import tempfile

def is_admin() -> bool:
    """检查当前进程是否拥有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def auto_elevate() -> bool:
    """
    在程序启动时自动尝试请求 UAC 提权。
    如果当前已具备管理员权限，直接返回 True。
    如果当前非管理员，则弹出 Windows UAC 管理员提权确认框：
    - 若用户选择“是”，则由 Windows 启动提权后的新进程，当前进程退出；
    - 若用户选择“否”，则返回 False，程序在普通权限下继续运行。
    """
    if is_admin():
        return True
    
    if "--no-elevate" in sys.argv:
        return False

    try:
        script = os.path.abspath(sys.argv[0])
        script_dir = os.path.dirname(script)
        params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
        
        # 请求 UAC 提权运行
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            f'"{script}" {params}'.strip(),
            script_dir,
            1  # SW_SHOWNORMAL
        )
        if ret > 32:
            # 提权成功，退出当前非特权进程
            sys.exit(0)
            return True
        return False
    except Exception as e:
        print(f"自动请求 UAC 失败: {e}")
        return False

def restart_as_admin() -> bool:
    """手动点击时以管理员身份重新启动当前程序"""
    if is_admin():
        return True
    try:
        script = os.path.abspath(sys.argv[0])
        script_dir = os.path.dirname(script)
        params = ' '.join([f'"{arg}"' for arg in sys.argv[1:] if arg != "--no-elevate"])
        
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            f'"{script}" {params}'.strip(),
            script_dir,
            1
        )
        if ret > 32:
            sys.exit(0)
            return True
        return False
    except Exception as e:
        print(f"UAC提权启动失败: {e}")
        return False

def run_powershell_script(script: str) -> tuple[bool, str]:
    """
    执行指定的 PowerShell 命令。
    如果当前是管理员，则直接在后台执行；
    如果当前非管理员，则弹出 UAC 提权执行。
    """
    if is_admin():
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            return res.returncode == 0, (res.stdout + "\n" + res.stderr).strip()
        except Exception as e:
            return False, str(e)

    # 非管理员模式：借助临时脚本和 Start-Process -Verb RunAs
    try:
        with tempfile.NamedTemporaryFile(suffix=".ps1", delete=False, mode="w", encoding="utf-8") as f:
            f.write(script)
            temp_ps1 = f.name

        out_file = temp_ps1 + ".out.txt"
        wrapper = f'try {{ & "{temp_ps1}" *>&1 | Out-File -FilePath "{out_file}" -Encoding utf8 }} finally {{}}'
        cmd = f'Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden -ArgumentList "-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command \"{wrapper}\""'
        
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True)
        
        out_content = ""
        if os.path.exists(out_file):
            try:
                with open(out_file, "r", encoding="utf-8", errors="replace") as rf:
                    out_content = rf.read()
                os.remove(out_file)
            except Exception:
                pass
        if os.path.exists(temp_ps1):
            try:
                os.remove(temp_ps1)
            except Exception:
                pass
        return True, out_content.strip()
    except Exception as e:
        return False, str(e)
