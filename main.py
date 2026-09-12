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

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from core.uac_manager import auto_elevate
from ui.main_window import MainWindow

def main():
    # 启动时自动请求 Windows 管理员权限 (UAC 弹窗)
    # 若用户点击“是”，会自动调起管理员进程并退出当前进程；若点击“否”，则以普通权限继续运行
    auto_elevate()

    # 启用高分屏 (High DPI) 缩放
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("ProcessNetLimiter")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
