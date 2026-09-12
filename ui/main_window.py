# -*- coding: utf-8 -*-
"""
主窗口界面逻辑
实现：
- 进程列表实时渲染与置顶展示
- 搜索与多维度分类筛选
- 上传与下载独立或同步限速设置（完全断开、1KB/s, 100KB/s, 1000KB/s, 自定义）
- 批量多选、一键应用、取消选中、一键解除所有限制
- UAC 状态栏与一键提权
"""
import os
import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QDoubleSpinBox, QCheckBox, QFrame, QMessageBox,
    QStatusBar, QButtonGroup
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon

from core.uac_manager import is_admin, restart_as_admin
from core.limiter_engine import LimiterEngine
from core.process_scanner import scan_processes, ProcessItem
from ui.process_table import ProcessTableWidget
from ui.styles import DARK_THEME_QSS

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = LimiterEngine()
        self.current_filter_category = "ALL"
        self._init_window()
        self._init_ui()
        self.refresh_processes()

        # 自动刷新定时器 (默认 4 秒刷新一次)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_auto_refresh)
        if self.auto_refresh_cb.isChecked():
            self.timer.start(4000)

    def _init_window(self):
        self.setWindowTitle("进程网络限速助手 (ProcessNetLimiter) - 专业版")
        self.resize(1100, 720)
        self.setMinimumSize(850, 580)
        self.setStyleSheet(DARK_THEME_QSS)

    def _init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # 1. 顶部栏 (标题、管理员权限徽章、搜索与刷新)
        header_card = QFrame()
        header_card.setObjectName("HeaderCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(12)

        title_label = QLabel("⚡ 进程网络限速助手")
        title_label.setObjectName("AppTitle")
        header_layout.addWidget(title_label)

        # 管理员权限指示与按钮
        self.admin_btn = QPushButton()
        if is_admin():
            self.admin_btn.setObjectName("AdminBadgeOk")
            self.admin_btn.setText("🛡️ 已获得管理员权限 (全功能就绪)")
            # 已移除悬浮提示框
        else:
            self.admin_btn.setObjectName("AdminBadgeWarn")
            self.admin_btn.setText("⚠️ 未获取管理员权限 (点击以管理员身份重启)")
            # 已移除悬浮提示框
            self.admin_btn.clicked.connect(self._on_request_admin)
        header_layout.addWidget(self.admin_btn)

        header_layout.addStretch()

        # 搜索输入框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索进程名、PID 或路径...")
        self.search_input.setFixedWidth(240)
        self.search_input.textChanged.connect(self._on_search_changed)
        header_layout.addWidget(self.search_input)

        # 自动刷新复选框
        self.auto_refresh_cb = QCheckBox("自动刷新")
        self.auto_refresh_cb.setChecked(False)
        self.auto_refresh_cb.stateChanged.connect(self._on_auto_refresh_toggle)
        header_layout.addWidget(self.auto_refresh_cb)

        # 手动刷新按钮
        self.refresh_btn = QPushButton("🔄 刷新进程")
        self.refresh_btn.clicked.connect(self.refresh_processes)
        header_layout.addWidget(self.refresh_btn)

        main_layout.addWidget(header_card)

        # 2. 分类筛选标签栏与批量选择操作
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        self.filter_group = QButtonGroup(self)
        self.filter_group.setExclusive(True)

        chips = [
            ("全部程序", "ALL"),
            ("⚡ 筛选下载器", "DOWNLOADER"),
            ("☁️ 筛选网盘", "CLOUD_DRIVE"),
            ("🎮 筛选游戏", "GAME"),
            ("⛔ 筛选已限制", "LIMITED"),
        ]

        for i, (label, tag) in enumerate(chips):
            btn = QPushButton(label)
            btn.setObjectName("FilterChip")
            btn.setCheckable(True)
            if i == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, t=tag: self._on_filter_chip_clicked(t))
            self.filter_group.addButton(btn, i)
            filter_bar.addWidget(btn)

        filter_bar.addStretch()

        # 快捷选择按钮
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(lambda: self.table.select_all(True))
        filter_bar.addWidget(self.select_all_btn)

        self.invert_btn = QPushButton("反选")
        self.invert_btn.clicked.connect(lambda: self.table.invert_selection())
        filter_bar.addWidget(self.invert_btn)

        self.clear_sel_btn = QPushButton("全不选")
        self.clear_sel_btn.clicked.connect(lambda: self.table.select_all(False))
        filter_bar.addWidget(self.clear_sel_btn)

        main_layout.addLayout(filter_bar)

        # 3. 进程数据表格
        self.table = ProcessTableWidget()
        self.table.selectionChangedCustom.connect(self._on_selection_changed)
        main_layout.addWidget(self.table, 1)

        # 4. 底部限速操作控制面板
        control_card = QFrame()
        control_card.setObjectName("ControlCard")
        ctrl_layout = QVBoxLayout(control_card)
        ctrl_layout.setContentsMargins(16, 12, 16, 12)
        ctrl_layout.setSpacing(10)

        # 控制栏上部：已选择摘要与分离设置开关
        top_ctrl_row = QHBoxLayout()
        self.selected_summary_label = QLabel("已选择 0 个程序")
        self.selected_summary_label.setObjectName("SectionTitle")
        top_ctrl_row.addWidget(self.selected_summary_label)

        top_ctrl_row.addSpacing(20)

        self.separate_cb = QCheckBox("⚙️ 分别设置上传和下载速度 (支持独立配置)")
        self.separate_cb.setChecked(False)
        self.separate_cb.stateChanged.connect(self._on_separate_toggle)
        top_ctrl_row.addWidget(self.separate_cb)

        top_ctrl_row.addStretch()
        ctrl_layout.addLayout(top_ctrl_row)

        # 控制栏下部：速度配置行与操作按钮
        settings_row = QHBoxLayout()
        settings_row.setSpacing(12)

        # 上传速度设置组
        self.up_group_widget = QWidget()
        up_layout = QHBoxLayout(self.up_group_widget)
        up_layout.setContentsMargins(0, 0, 0, 0)
        up_layout.setSpacing(6)
        
        self.up_title = QLabel("速度限制:")
        up_layout.addWidget(self.up_title)

        self.up_combo = QComboBox()
        self.up_combo.addItems([
            "完全断开连接 (0 KB/s - 阻断连接)",
            "1 KB/s (极限限速)",
            "100 KB/s (低速限制)",
            "1000 KB/s (中速限制 / ~1MB/s)",
            "自定义速度限制...",
            "不进行限制"
        ])
        self.up_combo.setCurrentIndex(2)  # 默认 100 KB/s
        self.up_combo.currentIndexChanged.connect(self._on_up_combo_changed)
        up_layout.addWidget(self.up_combo)

        self.up_spin = QDoubleSpinBox()
        self.up_spin.setRange(0.1, 99999.0)
        self.up_spin.setValue(500.0)
        self.up_spin.setVisible(False)
        up_layout.addWidget(self.up_spin)

        self.up_unit = QComboBox()
        self.up_unit.addItems(["KB/s", "MB/s"])
        self.up_unit.setVisible(False)
        up_layout.addWidget(self.up_unit)

        settings_row.addWidget(self.up_group_widget)

        # 下载速度设置组 (独立模式时展现)
        self.dl_group_widget = QWidget()
        dl_layout = QHBoxLayout(self.dl_group_widget)
        dl_layout.setContentsMargins(0, 0, 0, 0)
        dl_layout.setSpacing(6)

        dl_title = QLabel("下载限制:")
        dl_layout.addWidget(dl_title)

        self.dl_combo = QComboBox()
        self.dl_combo.addItems([
            "完全断开连接 (0 KB/s - 阻断连接)",
            "1 KB/s (极限限速)",
            "100 KB/s (低速限制)",
            "1000 KB/s (中速限制 / ~1MB/s)",
            "自定义速度限制...",
            "不限制下载"
        ])
        self.dl_combo.setCurrentIndex(2)
        self.dl_combo.currentIndexChanged.connect(self._on_dl_combo_changed)
        dl_layout.addWidget(self.dl_combo)

        self.dl_spin = QDoubleSpinBox()
        self.dl_spin.setRange(0.1, 99999.0)
        self.dl_spin.setValue(1000.0)
        self.dl_spin.setVisible(False)
        dl_layout.addWidget(self.dl_spin)

        self.dl_unit = QComboBox()
        self.dl_unit.addItems(["KB/s", "MB/s"])
        self.dl_unit.setVisible(False)
        dl_layout.addWidget(self.dl_unit)

        self.dl_group_widget.setVisible(False)
        settings_row.addWidget(self.dl_group_widget)

        settings_row.addStretch()

        # 操作按钮
        self.apply_btn = QPushButton("🚀 应用限速")
        self.apply_btn.setObjectName("ApplyBtn")
        self.apply_btn.clicked.connect(self._on_apply_limits)
        settings_row.addWidget(self.apply_btn)

        self.remove_selected_btn = QPushButton("❌ 取消选中限制")
        self.remove_selected_btn.clicked.connect(self._on_remove_selected)
        settings_row.addWidget(self.remove_selected_btn)

        self.reset_all_btn = QPushButton("⚡ 一键解除全部限制")
        self.reset_all_btn.setObjectName("ResetAllBtn")
        self.reset_all_btn.clicked.connect(self._on_reset_all)
        settings_row.addWidget(self.reset_all_btn)

        ctrl_layout.addLayout(settings_row)
        main_layout.addWidget(control_card)

        # 5. 底部状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪。提示：勾选进程后即可配置限速或断网。")

    def refresh_processes(self):
        """重新扫描进程与活动策略"""
        policies = self.engine.get_active_policies()
        items = scan_processes(policies)
        self.table.update_data(items)
        
        limited_count = sum(1 for it in items if it.is_limited)
        active_conn_count = sum(1 for it in items if it.connections_count > 0)
        self.status_bar.showMessage(f"已刷新 | 总进程: {len(items)} | 活跃联网进程: {active_conn_count} | 当前已限制: {limited_count}")

    def _on_auto_refresh(self):
        self.refresh_processes()

    def _on_auto_refresh_toggle(self, state):
        if state == Qt.Checked:
            self.timer.start(4000)
            self.status_bar.showMessage("已开启自动刷新 (每 4 秒)")
        else:
            self.timer.stop()
            self.status_bar.showMessage("已关闭自动刷新")

    def _on_search_changed(self, text):
        self.table.apply_filter(text, self.current_filter_category)

    def _on_filter_chip_clicked(self, category_tag):
        self.current_filter_category = category_tag
        self.table.apply_filter(self.search_input.text(), self.current_filter_category)

    def _on_selection_changed(self, count):
        self.selected_summary_label.setText(f"已选择 {count} 个程序")

    def _on_separate_toggle(self, state):
        is_separate = (state == Qt.Checked)
        self.dl_group_widget.setVisible(is_separate)
        if is_separate:
            self.up_title.setText("上传限制:")
        else:
            self.up_title.setText("速度限制 (上传与下载联动):")

    def _on_up_combo_changed(self, index):
        is_custom = (index == 4)  # 自定义速度限制
        self.up_spin.setVisible(is_custom)
        self.up_unit.setVisible(is_custom)

    def _on_dl_combo_changed(self, index):
        is_custom = (index == 4)  # 自定义速度限制
        self.dl_spin.setVisible(is_custom)
        self.dl_unit.setVisible(is_custom)

    def _on_request_admin(self):
        """以管理员身份重新启动"""
        if restart_as_admin():
            sys.exit(0)
        else:
            QMessageBox.warning(self, "提权提示", "未能获取管理员权限。请右键本程序并选择【以管理员身份运行】。")

    def _parse_speed_choice(self, combo_idx: int) -> str:
        mapping = {
            0: "block",
            1: "1kb",
            2: "100kb",
            3: "1000kb",
            4: "custom",
            5: "none"
        }
        return mapping.get(combo_idx, "none")

    def _on_apply_limits(self):
        """批量合并应用速度限制或断开连接 (无感极速下发)"""
        selected = self.table.get_selected_items()
        if not selected:
            QMessageBox.information(self, "提示", "请先在上方列表中勾选需要限制网络的一个或多个程序！")
            return

        is_separate = self.separate_cb.isChecked()
        up_choice = self._parse_speed_choice(self.up_combo.currentIndex())
        dl_choice = self._parse_speed_choice(self.dl_combo.currentIndex()) if is_separate else up_choice

        up_val = self.up_spin.value()
        up_unit = self.up_unit.currentText()
        dl_val = self.dl_spin.value() if is_separate else up_val
        dl_unit = self.dl_unit.currentText() if is_separate else up_unit

        from core.limiter_engine import LimitRequest
        requests = [
            LimitRequest(
                app_name=item.name,
                app_path=item.exe_path,
                upload_speed_type=up_choice,
                download_speed_type=dl_choice,
                custom_upload_val=up_val,
                custom_upload_unit=up_unit,
                custom_download_val=dl_val,
                custom_download_unit=dl_unit
            )
            for item in selected
        ]

        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            ok, msg = self.engine.apply_limits_batch(requests)
        finally:
            QApplication.restoreOverrideCursor()

        self.refresh_processes()
        if ok:
            self.status_bar.showMessage(f"已成功为 {len(requests)} 个程序下发并生效网络限制策略！")
        else:
            QMessageBox.warning(self, "策略应用失败", msg)

    def _on_remove_selected(self):
        """批量取消选中程序的限制 (极速执行)"""
        selected = self.table.get_selected_items()
        if not selected:
            QMessageBox.information(self, "提示", "请先在列表中勾选要解除限制的程序！")
            return

        app_names = [item.name for item in selected]
        
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import Qt
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            ok, msg, count = self.engine.remove_limits_batch(app_names)
        finally:
            QApplication.restoreOverrideCursor()

        self.refresh_processes()
        self.status_bar.showMessage(f"已成功为 {count} 个程序解除限制，网络恢复正常！")

    def _on_reset_all(self):
        """一键解除全部限制 (带安全检查与即时反馈)"""
        reply = QMessageBox.question(
            self,
            "确认解除所有限制",
            "确定要一键清空系统中所有由本工具设置的 QoS 速度限制与网络阻断规则吗？\n此操作将确保所有程序的网络恢复初始无限制状态。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtCore import Qt
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                ok, msg, count = self.engine.remove_all_limits()
            finally:
                QApplication.restoreOverrideCursor()

            self.refresh_processes()
            if ok:
                QMessageBox.information(
                    self,
                    "操作成功",
                    f"已成功一键解除系统中所有限速与阻断策略 (清理了 {count} 项规则)！\n当前系统中已无任何残留限制，所有程序网络均处于正常无限制状态。"
                )
                self.status_bar.showMessage("已成功解除全部限制，所有程序网络恢复正常。")
            else:
                QMessageBox.warning(self, "操作失败", msg)
