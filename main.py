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

def main():
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

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
