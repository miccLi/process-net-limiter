# -*- coding: utf-8 -*-
"""
主窗口逻辑 (现代化高分屏适配与国际化架构)
- 多级进程家族树状列表 (折叠展开与多级勾选)
- 异步工作线程 (QThread)，彻底消除策略下发与扫描时的界面卡顿
- 全面适配各种屏幕分辨率与 Windows 缩放设置 (Per-Monitor High-DPI)
- 完整的中英文双语切换与配置持久化 (i18n)
- 现代暗色质感界面 (Fluent Dark & Glassmorphism Aesthetics)
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
from core.process_scanner import scan_and_group_processes, ProcessFamily, get_running_app_paths
from core.i18n import t, i18n
from ui.process_tree import ProcessTreeWidget
from ui.system_tray import SystemTrayManager
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
            time_suffix = f" ({duration:.2f}s)"
            msg_with_time = f"{msg}{time_suffix}"
            self.finishedSignal.emit(ok, msg_with_time, payload)
        except Exception as e:
            self.finishedSignal.emit(False, f"Error: {e}", None)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.engine = EngineManager()
        self.current_filter_category = "ALL"
        self._active_worker = None
        self._scan_worker = None
        self._last_families = []
        self._force_quit = False
        self._first_minimize_notified = False
        self._rebound_performed = False

        self._init_window()
        self._init_ui()


        # 系统托盘初始化 (支持后台常驻、一键紧急恢复、气泡通知)
        self.tray = SystemTrayManager(self)
        self.tray.restoreAllRequested.connect(self._on_emergency_restore_all)
        self.tray.exitRequested.connect(self._on_tray_exit)
        self.tray.show()

        self.retranslate_ui()
        self.refresh_processes()

        # 自动刷新定时器 (可选开启，默认每 5 秒低频刷新)
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self._on_auto_refresh)

        # 实时网络测速定时器 (1 秒周期驱动计算与微刷新)
        self.speed_timer = QTimer(self)
        self.speed_timer.timeout.connect(self._on_speed_tick)
        self.speed_timer.start(1000)


    def _init_window(self):
        # 屏幕分辨率自适应：根据用户当前活动桌面可用区域智能计算最佳初始窗口大小
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            target_w = min(1220, max(940, int(geom.width() * 0.82)))
            target_h = min(820, max(620, int(geom.height() * 0.82)))
            self.resize(target_w, target_h)
            self.setMinimumSize(min(860, geom.width()), min(560, geom.height()))
        else:
            self.resize(1180, 760)
            self.setMinimumSize(920, 600)

        self.setStyleSheet(DARK_THEME_QSS)

    def _init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # 1. 顶部状态栏与权限/引擎控制卡片
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self.title_label = QLabel("进程网络限制器")
        self.title_label.setObjectName("AppTitle")
        top_bar.addWidget(self.title_label)

        self.sub_title = QLabel("支持多进程家族折叠、精确上下行分离限速与断网")
        self.sub_title.setObjectName("SubTitle")
        top_bar.addWidget(self.sub_title)

        top_bar.addStretch()

        # 语言切换选择器 (Bilingual Switcher)
        self.lang_combo = QComboBox()
        self.lang_combo.setObjectName("LangSelector")
        self.lang_combo.addItem("🇨🇳 中文", "zh_CN")
        self.lang_combo.addItem("🇬🇧 English", "en_US")
        curr_idx = 0 if i18n.current_lang == "zh_CN" else 1
        self.lang_combo.setCurrentIndex(curr_idx)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        top_bar.addWidget(self.lang_combo)

        # 引擎架构状态指示徽章
        self.engine_badge = QLabel(self.engine.active_engine_display)
        self.engine_badge.setObjectName("EngineBadge")
        top_bar.addWidget(self.engine_badge)

        # 全局实时网络吞吐看板徽章
        self.traffic_badge = QLabel("↑ 0 B/s   ↓ 0 B/s")
        self.traffic_badge.setObjectName("TrafficBadge")
        top_bar.addWidget(self.traffic_badge)

        # 管理员权限指示按钮
        self.admin_btn = QPushButton()
        if is_admin():
            self.admin_btn.setObjectName("AdminBadgeOk")
            self.admin_btn.setEnabled(False)
        else:
            self.admin_btn.setObjectName("AdminBadgeWarn")
            self.admin_btn.clicked.connect(self._on_request_admin)
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
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)
        filter_bar.addWidget(self.search_input, 3)

        # 分类筛选按钮组 (芯片风格)
        self.filter_group = QButtonGroup(self)
        self.filter_group.setExclusive(True)

        self.filter_categories = [
            ("filter_all", "ALL"),
            ("filter_limited", "LIMITED"),
            ("filter_downloader", "DOWNLOADER"),
            ("filter_cloud_drive", "CLOUD_DRIVE"),
            ("filter_game", "GAME"),
            ("filter_browser_social", "BROWSER_SOCIAL"),
        ]

        self.filter_buttons = []
        for i, (key, tag) in enumerate(self.filter_categories):
            btn = QPushButton(t(key))
            btn.setObjectName("FilterChip")
            btn.setCheckable(True)
            if i == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, t_tag=tag: self._on_filter_chip_clicked(t_tag))
            self.filter_group.addButton(btn, i)
            self.filter_buttons.append((btn, key))
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

        # 4. 底部限速操作控制面板卡片
        control_card = QFrame()
        control_card.setObjectName("ControlCard")
        ctrl_layout = QVBoxLayout(control_card)
        ctrl_layout.setContentsMargins(18, 14, 18, 14)
        ctrl_layout.setSpacing(10)

        # 控制栏上部：已选择摘要与分离设置开关
        top_ctrl_row = QHBoxLayout()
        self.selected_summary_label = QLabel("已选择 0 个程序/家族")
        self.selected_summary_label.setObjectName("SectionTitle")
        top_ctrl_row.addWidget(self.selected_summary_label)

        top_ctrl_row.addSpacing(24)

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

        self.dl_title = QLabel("下载限制:")
        dl_layout.addWidget(self.dl_title)

        self.dl_combo = QComboBox()
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

        # 原理与机制温馨提示卡片
        tip_frame = QFrame()
        tip_frame.setObjectName("TipBanner")
        tip_layout = QHBoxLayout(tip_frame)
        tip_layout.setContentsMargins(10, 6, 10, 6)
        
        self.tip_label = QLabel()
        self.tip_label.setWordWrap(True)
        tip_layout.addWidget(self.tip_label)
        ctrl_layout.addWidget(tip_frame)

        main_layout.addWidget(control_card)

        # 5. 底部状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def retranslate_ui(self):
        """全面更新界面上所有的文本信息 (支持中英文无缝切换)"""
        self.setWindowTitle(t("app_window_title"))
        self.title_label.setText(t("app_title"))
        self.sub_title.setText(t("app_subtitle"))
        self.refresh_btn.setText(t("refresh_btn"))
        self.auto_refresh_cb.setText(t("auto_refresh"))
        self.search_input.setPlaceholderText(t("search_placeholder"))
        if hasattr(self, "traffic_badge"):
            self.traffic_badge.setToolTip(t("global_traffic_label", up="Upload", down="Download"))

        # 更新筛选芯片文本
        for btn, key in self.filter_buttons:
            btn.setText(t(key))

        # 快捷选择
        self.select_all_btn.setText(t("select_all"))
        self.invert_btn.setText(t("invert_sel"))
        self.clear_sel_btn.setText(t("clear_sel"))

        # 树视图更新表头与节点
        self.tree.retranslate_ui()

        # 管理员按钮
        if is_admin():
            self.admin_btn.setText(t("admin_granted"))
        else:
            self.admin_btn.setText(t("admin_needed"))

        # 控制面板
        self.separate_cb.setText(t("separate_checkbox"))
        if self.separate_cb.isChecked():
            self.up_title.setText(t("upload_limit_label"))
        else:
            self.up_title.setText(t("speed_limit_label"))
        self.dl_title.setText(t("download_limit_label"))

        # 刷新速度下拉框预设选项
        cur_up = self.up_combo.currentIndex() if self.up_combo.count() > 0 else 2
        self.up_combo.blockSignals(True)
        self.up_combo.clear()
        self.up_combo.addItems([
            t("preset_block"),
            t("preset_1kb"),
            t("preset_100kb"),
            t("preset_1000kb"),
            t("preset_custom"),
            t("preset_none_up")
        ])
        self.up_combo.setCurrentIndex(max(0, cur_up))
        self.up_combo.blockSignals(False)

        cur_dl = self.dl_combo.currentIndex() if self.dl_combo.count() > 0 else 2
        self.dl_combo.blockSignals(True)
        self.dl_combo.clear()
        self.dl_combo.addItems([
            t("preset_block"),
            t("preset_1kb"),
            t("preset_100kb"),
            t("preset_1000kb"),
            t("preset_custom"),
            t("preset_none_dl")
        ])
        self.dl_combo.setCurrentIndex(max(0, cur_dl))
        self.dl_combo.blockSignals(False)

        self.apply_btn.setText(t("btn_apply"))
        self.remove_selected_btn.setText(t("btn_remove_selected"))
        self.reset_all_btn.setText(t("btn_reset_all"))

        # 刷新已选择摘要
        selected_count = len(self.tree.get_selected_targets())
        self.selected_summary_label.setText(t("selected_summary", count=selected_count))

        # 引擎提示更新
        self._update_engine_status_and_tip()

        # 状态栏
        if not self._last_families:
            self.status_bar.showMessage(t("ready_tip"))
        else:
            self._update_status_bar_metrics()

        # 托盘菜单文字同步更新
        if hasattr(self, "tray") and self.tray:
            self.tray.retranslate_ui()


    def _on_language_changed(self, index):
        lang_code = self.lang_combo.currentData()
        i18n.set_language(lang_code)
        self.retranslate_ui()

    def _set_busy(self, busy: bool, action_desc: str = ""):
        """设置界面异步繁忙状态，禁用操作按钮防止重复提交，保持主窗口 60FPS 极速响应"""
        self.apply_btn.setEnabled(not busy)
        self.remove_selected_btn.setEnabled(not busy)
        self.reset_all_btn.setEnabled(not busy)
        self.refresh_btn.setEnabled(not busy)

        if busy:
            self.apply_btn.setText(t("btn_apply_busy", action=action_desc))
            self.status_bar.showMessage(t("busy_applying", action=action_desc))
        else:
            self.apply_btn.setText(t("btn_apply"))

    def _update_engine_status_and_tip(self):
        """根据当前激活引擎与兼容性诊断动态更新顶部徽章与底部说明文案"""
        if not hasattr(self, "engine_badge") or not hasattr(self, "tip_label"):
            return
        self.engine_badge.setText(self.engine.active_engine_display)
        if self.engine.active_engine_name == "WINDIVERT":
            self.engine_badge.setStyleSheet(
                "background-color: #0c4a6e; color: #38bdf8; border: 1px solid #0284c7; "
                "padding: 4px 12px; border-radius: 14px; font-weight: bold; font-size: 11px;"
            )
            tip_msg = t("engine_tip_windivert")
        elif getattr(self.engine, "is_downgraded", False):
            self.engine_badge.setStyleSheet(
                "background-color: #451a03; color: #fcd34d; border: 1px solid #d97706; "
                "padding: 4px 12px; border-radius: 14px; font-weight: bold; font-size: 11px;"
            )
            reason = getattr(self.engine, "downgrade_reason", "驱动初始化受阻")
            tip_msg = t("engine_tip_downgraded", reason=reason)
        else:
            self.engine_badge.setStyleSheet(
                "background-color: #064e3b; color: #34d399; border: 1px solid #10b981; "
                "padding: 4px 12px; border-radius: 14px; font-weight: bold; font-size: 11px;"
            )
            tip_msg = t("engine_tip_native")

        # 若处于游戏加速器/TUN 虚拟网卡环境，追加友好环境说明
        diag = getattr(self.engine, "diagnostic", None)
        if diag and diag.is_accelerator_environment:
            tip_msg += f"\n{t('network_compat_accelerator_detected')}"

        self.tip_label.setText(tip_msg)


    def refresh_processes(self):
        """重新扫描进程家族与活动策略 (异步执行，彻底避免窗体假死与重入)"""
        if hasattr(self, "_scan_worker") and self._scan_worker and self._scan_worker.isRunning():
            return
        self.refresh_btn.setEnabled(False)
        self.status_bar.showMessage(t("scanning_status"))

        def _do_scan():
            if not self._rebound_performed:
                try:
                    running_apps = get_running_app_paths()
                    self.engine.auto_rebind_persistent_rules(running_apps)
                except Exception:
                    pass
                self._rebound_performed = True

            policies = self.engine.get_active_policies()
            families = scan_and_group_processes(policies)
            return True, "Scan completed", families


        self._scan_worker = AsyncWorker(_do_scan)
        self._scan_worker.finishedSignal.connect(self._on_refresh_completed)
        self._scan_worker.start()

    def _on_refresh_completed(self, ok: bool, msg: str, families: list):
        self.refresh_btn.setEnabled(True)
        self._update_engine_status_and_tip()
        if ok and families is not None:
            self._last_families = families
            self.tree.update_data(families)
            self._update_status_bar_metrics()
        else:
            self.status_bar.showMessage(t("scan_failed"))

    def _update_status_bar_metrics(self):
        families = self._last_families
        total_procs = sum(len(f.children) for f in families)
        limited_count = sum(1 for f in families if f.is_limited)
        active_conn_count = sum(1 for f in families if f.total_connections > 0)
        self.status_bar.showMessage(
            t("scan_done_status", fams=len(families), procs=total_procs, conns=active_conn_count, limited=limited_count)
        )

    def _on_async_policy_op_finished(self, ok: bool, msg: str, policies: dict):
        """策略操作异步完成回调：直接利用回读的 policies 刷新视图，省去二次查询"""
        self._set_busy(False)
        self._update_engine_status_and_tip()
        if policies is not None:
            families = scan_and_group_processes(policies)
            self._last_families = families
            self.tree.update_data(families)
            limited_count = sum(1 for f in families if f.is_limited)
            self.status_bar.showMessage(t("op_finished", msg=msg, count=limited_count))
        else:
            self.refresh_processes()

        if not ok:
            QMessageBox.warning(self, t("op_error"), msg)

    def _on_auto_refresh(self):
        self.refresh_processes()

    def _on_auto_refresh_toggle(self, state):
        if state == Qt.Checked:
            self.scan_timer.start(5000)
            self.status_bar.showMessage(t("auto_refresh_on"))
        else:
            self.scan_timer.stop()
            self.status_bar.showMessage(t("auto_refresh_off"))

    def _on_search_changed(self, text):
        self.tree.apply_filter(text, self.current_filter_category)

    def _on_speed_tick(self):
        """每秒驱动一次实时网络吞吐与进程速率计算与界面刷新"""
        try:
            global_up, global_down = self.engine.tick_traffic_monitor()
            from core.speed_utils import format_byte_rate
            up_str = format_byte_rate(global_up)
            down_str = format_byte_rate(global_down)

            # 1. 刷新顶部全局看板
            if hasattr(self, "traffic_badge") and self.traffic_badge:
                self.traffic_badge.setText(f"↑ {up_str}   ↓ {down_str}")

            # 2. 刷新进程家族树的各应用速率列 (若窗口最小化到托盘隐藏，跳过DOM微刷新以降低CPU开销)
            if self.isVisible() and hasattr(self, "tree") and self.tree:
                app_rates = self.engine.get_process_rates()
                self.tree.update_speeds(app_rates)

            # 3. 动态刷新托盘悬浮提示 (全量统计所有受限家族，不受当前筛选过滤器影响)
            if hasattr(self, "tray") and self.tray and hasattr(self, "tree") and self.tree:
                limited_cnt = sum(1 for f in self.tree.families_data if f.is_limited)
                self.tray.update_tooltip_rates(up_str, down_str, limited_cnt)
        except Exception:
            pass


    def _on_filter_chip_clicked(self, category_tag):
        self.current_filter_category = category_tag
        self.tree.apply_filter(self.search_input.text(), self.current_filter_category)

    def _on_selection_changed(self, count):
        self.selected_summary_label.setText(t("selected_summary", count=count))

    def _on_separate_toggle(self, state):
        is_separate = (state == Qt.Checked)
        self.dl_group_widget.setVisible(is_separate)
        if is_separate:
            self.up_title.setText(t("upload_limit_label"))
        else:
            self.up_title.setText(t("speed_limit_label"))

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
            QMessageBox.warning(self, t("elevation_title"), t("elevation_failed"))

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
            QMessageBox.information(self, t("notice"), t("no_selection_warning"))
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

        self._set_busy(True, t("action_apply"))
        self._active_worker = AsyncWorker(self.engine.apply_limits_batch, requests)
        self._active_worker.finishedSignal.connect(self._on_async_policy_op_finished)
        self._active_worker.start()

    def _on_remove_selected(self):
        """取消选中程序的限制 (异步合并执行)"""
        if hasattr(self, "_active_worker") and self._active_worker and self._active_worker.isRunning():
            return

        targets = self.tree.get_selected_targets()
        if not targets:
            QMessageBox.information(self, t("notice"), t("no_selection_remove_warning"))
            return

        app_names = [name for name, _ in targets]
        self._set_busy(True, t("action_remove"))
        self._active_worker = AsyncWorker(self.engine.remove_limits_batch, app_names)
        self._active_worker.finishedSignal.connect(self._on_async_policy_op_finished)
        self._active_worker.start()

    def _on_reset_all(self):
        """一键重置全部限制 (异步合并执行)"""
        if hasattr(self, "_active_worker") and self._active_worker and self._active_worker.isRunning():
            return

        reply = QMessageBox.question(
            self,
            t("reset_confirm_title"),
            t("reset_confirm_text"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._set_busy(True, t("action_reset"))
            self._active_worker = AsyncWorker(self.engine.remove_all_limits)
            self._active_worker.finishedSignal.connect(self._on_async_policy_op_finished)
            self._active_worker.start()

    def closeEvent(self, event):
        """窗口关闭安全退出生命周期处理：优先最小化至系统托盘常驻，显式退出时彻底回收资源"""
        if not self._force_quit:
            # 最小化隐藏到系统托盘，保持后台限速持续生效
            event.ignore()
            self.hide()
            if hasattr(self, "tray") and self.tray:
                self.tray.update_visibility_action()
                if not self._first_minimize_notified:
                    self.tray.notify(t("tray_minimized_title"), t("tray_minimized_msg"))
                    self._first_minimize_notified = True
            return

        # 真正退出程序生命周期清理
        if hasattr(self, "tray") and self.tray:
            self.tray.hide()

        if hasattr(self, "scan_timer") and self.scan_timer.isActive():
            self.scan_timer.stop()

        if hasattr(self, "speed_timer") and self.speed_timer.isActive():
            self.speed_timer.stop()

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

    def _on_tray_exit(self):
        """从托盘菜单显式退出"""
        self._force_quit = True
        self.close()

    def _on_emergency_restore_all(self):
        """从托盘菜单触发一键紧急恢复网络"""
        if hasattr(self, "_active_worker") and self._active_worker and self._active_worker.isRunning():
            return

        def _do_restore():
            ok, msg, policies = self.engine.remove_all_limits()
            return ok, msg, policies

        self._set_busy(True, t("action_reset"))
        self._active_worker = AsyncWorker(_do_restore)
        self._active_worker.finishedSignal.connect(self._on_emergency_restore_finished)
        self._active_worker.start()

    def _on_emergency_restore_finished(self, ok: bool, msg: str, policies: dict):
        self._on_async_policy_op_finished(ok, msg, policies)
        if hasattr(self, "tray") and self.tray:
            self.tray.notify(t("tray_restore_title"), t("tray_restore_done"))

