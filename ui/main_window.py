# -*- coding: utf-8 -*-
"""
主窗口逻辑 (异步高性能架构)
- 多级进程家族树状列表 (折叠展开与多级勾选)
- 异步工作线程 (QThread)，彻底消除策略下发与扫描时的界面假死/卡顿
- 优化列排布 (核心信息在前，执行路径在后)
- 合并下发与单次回读 QoS 与防火墙策略
- UAC 状态与自动提权
"""
import os
import sys
import time
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QDoubleSpinBox, QCheckBox, QFrame, QMessageBox,
    QStatusBar, QButtonGroup, QApplication
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal

from core.uac_manager import is_admin, restart_as_admin
from core.engine_manager import EngineManager
from core.limiter_engine import LimitRequest
from core.process_scanner import scan_and_group_processes, ProcessFamily
from ui.process_tree import ProcessTreeWidget
from ui.styles import DARK_THEME_QSS


class AsyncWorker(QThread):
    """通用后台异步执行线程，防止阻塞 Qt 主事件循环"""
    finishedSignal = pyqtSignal(bool, str, object)  # success, message, payload

    def __init__(self, task_func, *args, **kwargs):
        super().__init__()
        self.task_func = task_func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        t0 = time.time()
        try:
            res = self.task_func(*self.args, **self.kwargs)
            duration = time.time() - t0
            if isinstance(res, tuple):
                if len(res) == 3:
                    ok, msg, payload = res[0], res[1], res[2]
                elif len(res) == 2:
                    ok, msg = res[0], res[1]
                    payload = None
                else:
                    ok, msg, payload = True, "", None
            else:
                ok, msg, payload = True, str(res), None
            # 将耗时信息附加在回调中
            msg_with_time = f"{msg} (耗时 {duration:.2f}s)"
            self.finishedSignal.emit(ok, msg_with_time, payload)
        except Exception as e:
            self.finishedSignal.emit(False, f"执行异常: {e}", None)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = EngineManager()
        self.current_filter_category = "ALL"
        self._active_worker = None
        self._init_window()
        self._init_ui()
        self.refresh_processes()

        # 自动刷新定时器 (可选开启，默认每 5 秒低频刷新)
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self._on_auto_refresh)

    def _init_window(self):
        self.setWindowTitle("进程网络限制器 (ProcessNetLimiter) - 专业版")
        self.resize(1180, 760)
        self.setMinimumSize(920, 600)
        self.setStyleSheet(DARK_THEME_QSS)

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(10)

        # 1. 顶部状态栏与权限提示条
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        title_label = QLabel("进程网络限制器")
        title_label.setObjectName("AppTitle")
        top_bar.addWidget(title_label)

        sub_title = QLabel("支持多进程家族折叠、精确上下行分离限速与断网")
        sub_title.setObjectName("SubTitle")
        top_bar.addWidget(sub_title)

        top_bar.addStretch()

        # 引擎架构状态指示
        self.engine_badge = QLabel(self.engine.active_engine_display)
        self.engine_badge.setObjectName("EngineBadge")
        self.engine_badge.setStyleSheet(
            "background-color: #1a252f; color: #3498db; border: 1px solid #2980b9; "
            "padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;"
        )
        top_bar.addWidget(self.engine_badge)

        # 管理员权限指示
        self.admin_btn = QPushButton()
        self.admin_btn.setObjectName("AdminBadge")
        if is_admin():
            self.admin_btn.setText("🛡️ 已获管理员权限")
            self.admin_btn.setEnabled(False)
            self.admin_btn.setStyleSheet("background-color: #27ae60; color: white; border: none; padding: 4px 10px; border-radius: 4px; font-weight: bold;")
        else:
            self.admin_btn.setText("⚠️ 未获取管理员权限 (点击提权)")
            self.admin_btn.clicked.connect(self._on_request_admin)
            self.admin_btn.setStyleSheet("background-color: #e67e22; color: white; border: none; padding: 4px 10px; border-radius: 4px; font-weight: bold;")
        top_bar.addWidget(self.admin_btn)

        # 刷新与自动扫描控制
        self.refresh_btn = QPushButton("🔄 刷新进程")
        self.refresh_btn.clicked.connect(self.refresh_processes)
        top_bar.addWidget(self.refresh_btn)

        self.auto_refresh_cb = QCheckBox("自动刷新 (5s)")
        self.auto_refresh_cb.setChecked(False)
        self.auto_refresh_cb.stateChanged.connect(self._on_auto_refresh_toggle)
        top_bar.addWidget(self.auto_refresh_cb)

        main_layout.addLayout(top_bar)

        # 2. 搜索与类别筛选栏
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 搜索程序名称、PID、可执行文件路径...")
        self.search_input.textChanged.connect(self._on_search_changed)
        filter_bar.addWidget(self.search_input, 2)

        # 分类筛选按钮组
        self.filter_group = QButtonGroup(self)
        self.filter_group.setExclusive(True)

        categories = [
            ("全部程序", "ALL"),
            ("⛔ 仅看已限制", "LIMITED"),
            ("🚀 下载器优先", "DOWNLOADER"),
            ("☁️ 网盘优先", "CLOUD_DRIVE"),
            ("🎮 游戏优先", "GAME"),
            ("🌐 浏览器与社交", "BROWSER_SOCIAL"),
        ]

        for i, (label, tag) in enumerate(categories):
            btn = QPushButton(label)
            btn.setCheckable(True)
            if i == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, t=tag: self._on_filter_chip_clicked(t))
            self.filter_group.addButton(btn, i)
            filter_bar.addWidget(btn)

        filter_bar.addStretch()

        # 快捷选择按钮
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(lambda: self.tree.select_all(True))
        filter_bar.addWidget(self.select_all_btn)

        self.invert_btn = QPushButton("反选")
        self.invert_btn.clicked.connect(lambda: self.tree.invert_selection())
        filter_bar.addWidget(self.invert_btn)

        self.clear_sel_btn = QPushButton("全不选")
        self.clear_sel_btn.clicked.connect(lambda: self.tree.select_all(False))
        filter_bar.addWidget(self.clear_sel_btn)

        main_layout.addLayout(filter_bar)

        # 3. 任务管理器风格的进程家族树状视图
        self.tree = ProcessTreeWidget()
        self.tree.selectionChangedCustom.connect(self._on_selection_changed)
        main_layout.addWidget(self.tree, 1)

        # 4. 底部限速操作控制面板
        control_card = QFrame()
        control_card.setObjectName("ControlCard")
        ctrl_layout = QVBoxLayout(control_card)
        ctrl_layout.setContentsMargins(16, 12, 16, 12)
        ctrl_layout.setSpacing(10)

        # 控制栏上部：已选择摘要与分离设置开关
        top_ctrl_row = QHBoxLayout()
        self.selected_summary_label = QLabel("已选择 0 个程序/家族")
        self.selected_summary_label.setObjectName("SectionTitle")
        top_ctrl_row.addWidget(self.selected_summary_label)

        top_ctrl_row.addSpacing(20)

        self.separate_cb = QCheckBox("⚙️ 分别设置上传和下载速度 (独立配置)")
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

        # 原理与机制温馨提示 (动态跟随当前激活引擎展示)
        self.tip_label = QLabel()
        self.tip_label.setStyleSheet("color: #718096; font-size: 11px; padding-top: 2px;")
        self.tip_label.setWordWrap(True)
        self._update_engine_status_and_tip()
        ctrl_layout.addWidget(self.tip_label)

        main_layout.addWidget(control_card)

        # 5. 底部状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪。提示：支持直接勾选进程家族批量限速，或展开家族仅限制某一特定进程。")

    def _set_busy(self, busy: bool, action_desc: str = ""):
        """设置界面异步繁忙状态，禁用操作按钮防止重复提交，同时保持主窗口 60FPS 极速响应"""
        self.apply_btn.setEnabled(not busy)
        self.remove_selected_btn.setEnabled(not busy)
        self.reset_all_btn.setEnabled(not busy)
        self.refresh_btn.setEnabled(not busy)

        if busy:
            self.apply_btn.setText(f"⏳ {action_desc}...")
            self.status_bar.showMessage(f"⏳ 正在{action_desc}，后台处理中，界面保持流畅响应...")
        else:
            self.apply_btn.setText("🚀 应用限速")

    def _update_engine_status_and_tip(self):
        """根据当前激活引擎动态更新顶部徽章与底部说明文案"""
        if not hasattr(self, "engine_badge") or not hasattr(self, "tip_label"):
            return
        self.engine_badge.setText(self.engine.active_engine_display)
        if self.engine.active_engine_name == "WINDIVERT":
            self.engine_badge.setStyleSheet(
                "background-color: #1a252f; color: #3498db; border: 1px solid #2980b9; "
                "padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;"
            )
            self.tip_label.setText(
                "💡 提示：当前已启用 WinDivert 内核级流量整形引擎 (NetLimiter 同级技术，秒级生效且支持游戏 UDP/TCP 严格卡死 1KB/s)。"
                "“完全断开连接”同时执行内核与防火墙双重物理阻断。"
            )
        else:
            self.engine_badge.setStyleSheet(
                "background-color: #142a1f; color: #2ecc71; border: 1px solid #27ae60; "
                "padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;"
            )
            self.tip_label.setText(
                "💡 提示：当前处于 Windows 原生系统策略引擎模式 (基于系统组策略 QoS 出站整形与高级安全防火墙)。"
                "出站限速内核级平稳生效，入站限速由 TCP 窗口协商节流，“完全断开连接”通过防火墙双向毫秒级物理阻断。"
            )

    def refresh_processes(self):
        """重新扫描进程家族与活动策略 (异步执行，彻底避免窗体假死与重入)"""
        if hasattr(self, "_scan_worker") and self._scan_worker and self._scan_worker.isRunning():
            return
        self.refresh_btn.setEnabled(False)
        self.status_bar.showMessage("正在获取活动策略并扫描进程家族...")

        def _do_scan():
            policies = self.engine.get_active_policies()
            families = scan_and_group_processes(policies)
            return True, "刷新完成", families

        self._scan_worker = AsyncWorker(_do_scan)
        self._scan_worker.finishedSignal.connect(self._on_refresh_completed)
        self._scan_worker.start()

    def _on_refresh_completed(self, ok: bool, msg: str, families: list):
        self.refresh_btn.setEnabled(True)
        self._update_engine_status_and_tip()
        if ok and families is not None:
            self.tree.update_data(families)
            total_procs = sum(len(f.children) for f in families)
            limited_count = sum(1 for f in families if f.is_limited)
            active_conn_count = sum(1 for f in families if f.total_connections > 0)
            self.status_bar.showMessage(
                f"已就绪 | 进程家族: {len(families)} | 总进程数: {total_procs} | 联网家族: {active_conn_count} | 已限制: {limited_count}"
            )
        else:
            self.status_bar.showMessage("刷新失败")

    def _on_async_policy_op_finished(self, ok: bool, msg: str, policies: dict):
        """策略操作异步完成回调：直接利用回读的 policies 刷新视图，省去二次查询"""
        self._set_busy(False)
        self._update_engine_status_and_tip()
        if policies is not None:
            families = scan_and_group_processes(policies)
            self.tree.update_data(families)
            limited_count = sum(1 for f in families if f.is_limited)
            self.status_bar.showMessage(f"✅ {msg} | 当前受限进程家族数: {limited_count}")
        else:
            self.refresh_processes()

        if not ok:
            QMessageBox.warning(self, "操作异常", msg)

    def _on_auto_refresh(self):
        self.refresh_processes()

    def _on_auto_refresh_toggle(self, state):
        if state == Qt.Checked:
            self.scan_timer.start(5000)
            self.status_bar.showMessage("已开启自动刷新 (每 5 秒)")
        else:
            self.scan_timer.stop()
            self.status_bar.showMessage("已关闭自动刷新")

    def _on_search_changed(self, text):
        self.tree.apply_filter(text, self.current_filter_category)

    def _on_filter_chip_clicked(self, category_tag):
        self.current_filter_category = category_tag
        self.tree.apply_filter(self.search_input.text(), self.current_filter_category)

    def _on_selection_changed(self, count):
        self.selected_summary_label.setText(f"已选择 {count} 个程序/家族")

    def _on_separate_toggle(self, state):
        is_separate = (state == Qt.Checked)
        self.dl_group_widget.setVisible(is_separate)
        if is_separate:
            self.up_title.setText("上传限制:")
        else:
            self.up_title.setText("速度限制 (上传与下载):")

    def _on_up_combo_changed(self, index):
        is_custom = (index == 4)
        self.up_spin.setVisible(is_custom)
        self.up_unit.setVisible(is_custom)

    def _on_dl_combo_changed(self, index):
        is_custom = (index == 4)
        self.dl_spin.setVisible(is_custom)
        self.dl_unit.setVisible(is_custom)

    def _on_request_admin(self):
        if restart_as_admin():
            sys.exit(0)
        else:
            QMessageBox.warning(self, "提权提示", "未能获取管理员权限。请右键选择“以管理员身份运行”。")

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
        """批量应用速度限制或断网 (异步执行，单次 PowerShell 合并回读)"""
        if hasattr(self, "_active_worker") and self._active_worker and self._active_worker.isRunning():
            return

        targets = self.tree.get_selected_targets()
        if not targets:
            QMessageBox.information(self, "提示", "请先在列表中勾选想要限制的程序或家族！")
            return

        is_separate = self.separate_cb.isChecked()
        up_choice = self._parse_speed_choice(self.up_combo.currentIndex())
        dl_choice = self._parse_speed_choice(self.dl_combo.currentIndex()) if is_separate else up_choice

        up_val = self.up_spin.value()
        up_unit = self.up_unit.currentText()
        dl_val = self.dl_spin.value() if is_separate else up_val
        dl_unit = self.dl_unit.currentText() if is_separate else up_unit

        requests = [
            LimitRequest(
                app_name=app_name,
                app_path=exe_path,
                upload_speed_type=up_choice,
                download_speed_type=dl_choice,
                custom_upload_val=up_val,
                custom_upload_unit=up_unit,
                custom_download_val=dl_val,
                custom_download_unit=dl_unit
            )
            for app_name, exe_path in targets
        ]

        self._set_busy(True, "下发策略")
        self._active_worker = AsyncWorker(self.engine.apply_limits_batch, requests)
        self._active_worker.finishedSignal.connect(self._on_async_policy_op_finished)
        self._active_worker.start()

    def _on_remove_selected(self):
        """取消选中程序的限制 (异步合并执行)"""
        if hasattr(self, "_active_worker") and self._active_worker and self._active_worker.isRunning():
            return

        targets = self.tree.get_selected_targets()
        if not targets:
            QMessageBox.information(self, "提示", "请先在列表中勾选想要解除限制的程序或家族！")
            return

        app_names = [name for name, _ in targets]
        self._set_busy(True, "解除限制")
        self._active_worker = AsyncWorker(self.engine.remove_limits_batch, app_names)
        self._active_worker.finishedSignal.connect(self._on_async_policy_op_finished)
        self._active_worker.start()

    def _on_reset_all(self):
        """一键重置全部限制 (异步合并执行)"""
        if hasattr(self, "_active_worker") and self._active_worker and self._active_worker.isRunning():
            return

        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要一键清除系统中所有由本程序设置的 QoS 速度限制与防火墙阻断规则吗？\n此操作将确保所有网络程序恢复原始无限制状态。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._set_busy(True, "一键清除策略")
            self._active_worker = AsyncWorker(self.engine.remove_all_limits)
            self._active_worker.finishedSignal.connect(self._on_async_policy_op_finished)
            self._active_worker.start()

    def closeEvent(self, event):
        """窗口关闭安全退出生命周期处理：终止定时器、回收异步 Worker、释放驱动资源"""
        if hasattr(self, "scan_timer") and self.scan_timer.isActive():
            self.scan_timer.stop()

        if hasattr(self, "_scan_worker") and self._scan_worker and self._scan_worker.isRunning():
            try:
                self._scan_worker.finishedSignal.disconnect()
            except Exception:
                pass
            self._scan_worker.quit()
            self._scan_worker.wait(400)

        if hasattr(self, "_active_worker") and self._active_worker and self._active_worker.isRunning():
            try:
                self._active_worker.finishedSignal.disconnect()
            except Exception:
                pass
            self._active_worker.quit()
            self._active_worker.wait(600)

        try:
            if hasattr(self, "engine") and self.engine:
                self.engine.stop()
        except Exception:
            pass

        event.accept()
