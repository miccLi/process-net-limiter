# -*- coding: utf-8 -*-
"""
程序启动入口
设置高分屏缩放自适应、启动自动检测与申请 UAC 权限，并渲染主窗口。
"""
import sys
import os

# 将项目根目录添加进 sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import ctypes
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtCore import Qt
from core.uac_manager import auto_elevate
from ui.main_window import MainWindow


def run_uninstall_cleanup() -> bool:
    """
    执行安装卸载/重置残留清理：
    1. 清除本地持久化规则与存储目录
    2. 清除 Windows 系统中所有 NetLimit_* QoS 策略与防火墙阻断
    3. 注销开机启动系统计划任务
    """
    print("[Cleanup] 正在执行 ProcessNetLimiter 卸载残留全面清理...")
    success = True
    try:
        from core.rules_store import RulesStore
        rs = RulesStore()
        rs.clear()
        print("[Cleanup] 已清空本地规则持久化数据库。")
    except Exception as e:
        print(f"[Cleanup] 清空持久化规则异常: {e}")
        success = False

    try:
        from core.limiter_engine import LimiterEngine
        le = LimiterEngine()
        ok, msg, _ = le.remove_all_limits()
        print(f"[Cleanup] 系统策略与防火墙清理结果: {msg}")
    except Exception as e:
        print(f"[Cleanup] 清理系统 QoS/防火墙异常: {e}")
        success = False

    try:
        from core.autostart_manager import set_autostart
        set_autostart(False)
        print("[Cleanup] 已注销开机启动计划任务。")
    except Exception as e:
        print(f"[Cleanup] 注销开机计划任务异常: {e}")

    print("[Cleanup] 卸载清理流程完成，所有系统网络策略已彻底恢复初始状态。")
    return success


def main():
    # 卸载清理模式：静默执行后直接退出，不创建任何 GUI 界面
    if "--uninstall-cleanup" in sys.argv or "--cleanup" in sys.argv:
        ok = run_uninstall_cleanup()
        sys.exit(0 if ok else 1)

    # 启动时自动请求 Windows 管理员权限 (UAC 弹窗)
    # 若用户点击“是”，会自动调起管理员进程并退出当前进程；若点击“否”，则以普通权限继续运行
    auto_elevate()


    # 1. Windows 原生 Per-Monitor DPI Aware v2 设置 (彻底解决 125%/150% 缩放模糊与多显示器拖拽伪影)
    if sys.platform == "win32":
        try:
            # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try:
                # Shcore 降级兼容: PROCESS_PER_MONITOR_DPI_AWARE = 2
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                pass

    # 2. 启用 Qt 高分屏 (High DPI) 缩放与高清像素图
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # 3. 避免 125% / 150% 缩放被粗暴四舍五入为 100% 或 200% (PassThrough 线性平滑缩放)
    if hasattr(QGuiApplication, "setHighDpiScaleFactorRoundingPolicy"):
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

    app = QApplication(sys.argv)
    app.setApplicationName("ProcessNetLimiter")
    # 允许在主窗口隐藏到托盘时保持进程常驻后台
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    if "--minimized" not in sys.argv:
        window.show()

    sys.exit(app.exec_())



if __name__ == "__main__":
    main()
