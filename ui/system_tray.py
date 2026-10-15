# -*- coding: utf-8 -*-
"""
系统托盘常驻与后台守护组件 (ui/system_tray.py)
- 提供 Windows 系统托盘常驻 (QSystemTrayIcon)
- 托盘右键菜单：显示/隐藏窗口、当前引擎状态展示、一键紧急恢复网络、开机静默启动开关、安全退出
- 支持托盘气泡通知 (Balloon Notification)
- 自适应中英文双语热重载 (i18n)
- 动态矢量质感托盘图标生成，完美适配 High-DPI 缩放
"""
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QFont
from PyQt5.QtCore import Qt, pyqtSignal

from core.i18n import t
from core.autostart_manager import is_autostart_enabled, set_autostart


def create_tray_pixmap(size: int = 64) -> QPixmap:
    """动态绘制高清晰度矢量质感托盘图标 (蓝紫电光科技盾牌 + 网络波形)"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # 1. 绘制主体外发光圆形底座
    margin = int(size * 0.08)
    rect_size = size - margin * 2
    painter.setBrush(QBrush(QColor("#0f172a")))
    painter.setPen(QPen(QColor("#38bdf8"), int(size * 0.06)))
    painter.drawRoundedRect(margin, margin, rect_size, rect_size, int(size * 0.28), int(size * 0.28))

    # 2. 绘制科技雷达网络环形波
    painter.setPen(QPen(QColor("#0284c7"), int(size * 0.05)))
    painter.setBrush(Qt.NoBrush)
    center = size / 2.0
    r1 = size * 0.22
    painter.drawEllipse(int(center - r1), int(center - r1), int(r1 * 2), int(r1 * 2))

    # 3. 绘制中心微光核心点
    painter.setBrush(QBrush(QColor("#38bdf8")))
    painter.setPen(Qt.NoPen)
    r_core = int(size * 0.10)
    painter.drawEllipse(int(center - r_core), int(center - r_core), r_core * 2, r_core * 2)

    # 4. 绘制闪电/限速标识折线
    painter.setPen(QPen(QColor("#f8fafc"), int(size * 0.07), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    points = [
        (int(size * 0.45), int(size * 0.28)),
        (int(size * 0.35), int(size * 0.52)),
        (int(size * 0.55), int(size * 0.52)),
        (int(size * 0.45), int(size * 0.74))
    ]
    for i in range(len(points) - 1):
        painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])

    painter.end()
    return pixmap


class SystemTrayManager(QSystemTrayIcon):
    restoreAllRequested = pyqtSignal()
    exitRequested = pyqtSignal()

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window

        # 动态创建高清托盘图标
        self.tray_icon = QIcon(create_tray_pixmap(64))
        self.setIcon(self.tray_icon)

        self._init_menu()
        self.retranslate_ui()

        # 托盘点击激活交互
        self.activated.connect(self._on_tray_activated)

    def _init_menu(self):
        self.menu = QMenu()
        self.menu.setStyleSheet("""
            QMenu {
                background-color: #161e2a;
                border: 1px solid #28374d;
                border-radius: 8px;
                padding: 6px;
                color: #f1f5f9;
                font-family: "Segoe UI", sans-serif;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #2563eb;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background-color: #28374d;
                margin: 4px 6px;
            }
            QMenu::item:disabled {
                color: #64748b;
            }
        """)

        # 1. 显示/隐藏窗口操作
        self.action_toggle = QAction(self)
        self.action_toggle.triggered.connect(self._toggle_window_visibility)
        self.menu.addAction(self.action_toggle)

        # 2. 引擎状态展示条目 (只读信息)
        self.action_engine = QAction(self)
        self.action_engine.setEnabled(False)
        self.menu.addAction(self.action_engine)

        self.menu.addSeparator()

        # 3. 紧急恢复所有网络
        self.action_restore = QAction(self)
        self.action_restore.triggered.connect(self._on_emergency_restore)
        self.menu.addAction(self.action_restore)

        self.menu.addSeparator()

        # 4. 开机静默自启复选框
        self.action_autostart = QAction(self)
        self.action_autostart.setCheckable(True)
        self.action_autostart.setChecked(is_autostart_enabled())
        self.action_autostart.triggered.connect(self._on_autostart_toggled)
        self.menu.addAction(self.action_autostart)

        self.menu.addSeparator()

        # 5. 退出程序
        self.action_exit = QAction(self)
        self.action_exit.triggered.connect(self._on_exit_clicked)
        self.menu.addAction(self.action_exit)

        # 菜单即将展现时动态刷新条目状态
        self.menu.aboutToShow.connect(self._on_menu_about_to_show)
        self.setContextMenu(self.menu)

    def _on_menu_about_to_show(self):
        """当托盘菜单即将弹出时，动态刷新窗口显示状态、引擎状态与开机自启复选状态"""
        self.update_visibility_action()
        self.action_autostart.setChecked(is_autostart_enabled())
        engine_name = self.main_window.engine.active_engine_display if hasattr(self.main_window, "engine") else "Active"
        self.action_engine.setText(f"⚙️ {engine_name}")

    def retranslate_ui(self):
        """动态更新托盘菜单文字与悬停提示"""
        is_visible = self.main_window.isVisible()
        self.action_toggle.setText(t("tray_hide") if is_visible else t("tray_show"))
        
        engine_name = self.main_window.engine.active_engine_display if hasattr(self.main_window, "engine") else "Active"
        self.action_engine.setText(f"⚙️ {engine_name}")

        self.action_restore.setText(t("tray_emergency_restore"))
        self.action_autostart.setText(t("tray_autostart"))
        self.action_exit.setText(t("tray_exit"))

        self.setToolTip(f"{t('app_title')} - {engine_name}")

    def update_visibility_action(self):
        """当主窗口显示或隐藏时同步更新托盘菜单选项文本"""
        is_visible = self.main_window.isVisible()
        self.action_toggle.setText(t("tray_hide") if is_visible else t("tray_show"))

    def _toggle_window_visibility(self):
        if self.main_window.isVisible():
            self.main_window.hide()
        else:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
        self.update_visibility_action()

    def _on_tray_activated(self, reason):
        # 单击或双击托盘图标切换窗口显示
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._toggle_window_visibility()

    def _on_emergency_restore(self):
        # 触发紧急恢复
        self.restoreAllRequested.emit()

    def _on_autostart_toggled(self, checked: bool):
        ok, msg = set_autostart(checked)
        if ok:
            notif = t("autostart_enabled_msg") if checked else t("autostart_disabled_msg")
            self.showMessage(t("app_title"), notif, QSystemTrayIcon.Information, 2500)
        else:
            # 失败时回滚勾选状态
            self.action_autostart.setChecked(not checked)
            self.showMessage(t("app_title"), f"Error: {msg}", QSystemTrayIcon.Warning, 3500)

    def _on_exit_clicked(self):
        self.exitRequested.emit()

    def notify(self, title: str, message: str, is_warn: bool = False, duration_ms: int = 3000):
        """向 Windows 发射原生系统托盘气泡提示"""
        icon = QSystemTrayIcon.Warning if is_warn else QSystemTrayIcon.Information
        self.showMessage(title, message, icon, duration_ms)

    def update_tooltip_rates(self, up_str: str, down_str: str, limited_count: int = 0):
        """动态更新托盘悬停提示（包含实时系统吞吐与当前受限进程数）"""
        tip = f"{t('app_title')}\n↑ {up_str} | ↓ {down_str}"
        if limited_count > 0:
            tip += f"\n{t('filter_limited')}: {limited_count}"
        self.setToolTip(tip)

