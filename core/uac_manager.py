# -*- coding: utf-8 -*-
"""
UAC 权限管理模块
检测当前是否以管理员权限运行，以及提供便捷的 UAC 提权与提权执行功能。
"""
import sys
import os
import ctypes
import subprocess
import tempfile

def is_admin() -> bool:
    """检查当前是否拥有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def auto_elevate() -> bool:
    """
    在程序启动时自动申请 UAC 提权。
    若当前已具备管理员权限，直接返回 True；
    若当前不是管理员，则弹出 Windows UAC 管理员提权确认框：
    - 用户选择“是”：Windows 将以管理员权限启动新进程，当前进程退出。
    - 用户选择“否”：则返回 False，程序降级以普通权限继续运行。
    """
    if is_admin():
        return True
    
    if "--no-elevate" in sys.argv:
        return False

    try:
        script = os.path.abspath(sys.argv[0])
        script_dir = os.path.dirname(script)
        params = ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
        
        # 申请 UAC 提权重新拉起程序
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            f'"{script}" {params}'.strip(),
            script_dir,
            1  # SW_SHOWNORMAL
        )
        if ret > 32:
            # 提权拉起成功，退出当前非特权进程
            sys.exit(0)
            return True
        return False
    except Exception as e:
        print(f"自动 UAC 失败: {e}")
        return False

def restart_as_admin() -> bool:
    """手动在运行时以管理员重启当前程序"""
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
        print(f"UAC提权重启失败: {e}")
        return False

def run_powershell_script(script: str) -> tuple[bool, str]:
    """
    执行指定的 PowerShell 脚本。
    优先使用免窗体快速子进程执行；若非管理员且执行失败，则调起 UAC 提权。
    """
    creation_flags = 0x08000000  # subprocess.CREATE_NO_WINDOW
    
    # 优先尝试直接执行 (快速、无窗体分配开销)
    try:
        res = subprocess.run(
            ["powershell", "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creation_flags
        )
        if res.returncode == 0:
            return True, (res.stdout + "\n" + res.stderr).strip()
        # 若是管理员且失败，直接返回错误信息
        if is_admin():
            return False, (res.stdout + "\n" + res.stderr).strip()
    except Exception as e:
        if is_admin():
            return False, str(e)

    # 非管理员模式下通过临时脚本与 Start-Process -Verb RunAs 提权
    try:
        with tempfile.NamedTemporaryFile(suffix=".ps1", delete=False, mode="w", encoding="utf-8") as f:
            f.write(script)
            temp_ps1 = f.name

        out_file = temp_ps1 + ".out.txt"
        wrapper = f'try {{ & "{temp_ps1}" *>&1 | Out-File -FilePath "{out_file}" -Encoding utf8 }} finally {{}}'
        cmd = f'Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden -ArgumentList "-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command \"{wrapper}\""'
        
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, creationflags=creation_flags)
        
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
