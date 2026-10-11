# -*- coding: utf-8 -*-
"""
多级进程家族树组件 (ProcessTreeWidget - 高分屏与国际化适配版)
类似 Windows 任务管理器的折叠树状结构：
- 第一级：进程家族 (聚合总连接数与限速状态，支持折叠展开)
- 第二级：家族子进程 (展示具体 PID 与执行文件路径)
- 清爽高效的列排布：复选框 -> 程序名称 -> 限制状态 (醒目前置) -> PID -> 类别 -> 网络连接 -> 执行文件路径
- 完美适配 Windows 高分屏缩放 (DPI-Aware) 与中英双语国际化 (i18n)
"""
from PyQt5.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QHeaderView, QAbstractItemView, QCheckBox, QWidget, QHBoxLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from core.process_scanner import ProcessFamily, ProcessItem, ProcessCategory
from core.i18n import t, i18n

# 列定义：核心信息前置，长路径右排
COL_CHECK = 0       # 复选框
COL_NAME = 1        # 程序名称 / 进程家族
COL_STATUS = 2      # 当前限制状态
COL_PID = 3         # PID
COL_CATEGORY = 4    # 类别徽章
COL_CONNS = 5       # 网络连接
COL_PATH = 6        # 执行文件路径


class TristateHeaderCheckBox(QCheckBox):
    """
    专为多子项家族节点设计的防误触三态复选框。
    用户手动点击时只在 Unchecked 与 Checked 之间切换，
    PartiallyChecked 状态仅由子进程实际勾选状态程序化联动驱动。
    """
    def nextCheckState(self):
        if self.checkState() == Qt.Checked:
            self.setCheckState(Qt.Unchecked)
        else:
            self.setCheckState(Qt.Checked)


def format_summary_i18n(summary: str) -> str:
    """根据当前语言环境自适应转换限速状态摘要文本"""
    if not summary or summary == "正常":
        return t("policy_normal")
    if summary in ("⛔ 完全断网", "⛔ 阻断"):
        return t("policy_blocked")
    if i18n.current_lang == "en_US":
        return summary.replace("上: ", "Up: ").replace("下: ", "Down: ")
    return summary


class ProcessTreeWidget(QTreeWidget):
    selectionChangedCustom = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.families_data: list[ProcessFamily] = []
        self.displayed_families: list[ProcessFamily] = []
        self.current_search = ""
        self.current_filter = "ALL"
        self._init_ui()

    def _init_ui(self):
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setRootIsDecorated(True)
        self.setAnimated(True)

        # 必须先设置列数和列头，QHeaderView 才能安全配置各 section
        self.retranslate_ui()

        header = self.header()
        header.setSectionResizeMode(COL_CHECK, QHeaderView.Fixed)
        header.setSectionResizeMode(COL_NAME, QHeaderView.Interactive)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.Interactive)
        header.setSectionResizeMode(COL_PID, QHeaderView.Interactive)
        header.setSectionResizeMode(COL_CATEGORY, QHeaderView.Interactive)
        header.setSectionResizeMode(COL_CONNS, QHeaderView.Interactive)
        header.setSectionResizeMode(COL_PATH, QHeaderView.Stretch)

        self._apply_column_widths()
        self.itemClicked.connect(self._on_item_clicked)


    def _apply_column_widths(self):
        """根据当前字体大小与 DPI 缩放计算自适应列宽"""
        fm = self.fontMetrics()
        scale = max(1.0, fm.height() / 16.0)
        self.setColumnWidth(COL_CHECK, int(42 * scale))
        self.setColumnWidth(COL_NAME, int(260 * scale))
        self.setColumnWidth(COL_STATUS, int(160 * scale))
        self.setColumnWidth(COL_PID, int(80 * scale))
        self.setColumnWidth(COL_CATEGORY, int(110 * scale))
        self.setColumnWidth(COL_CONNS, int(95 * scale))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 保持列比例合适
        if not hasattr(self, "_initialized_widths"):
            self._apply_column_widths()
            self._initialized_widths = True

    def retranslate_ui(self):
        """语言切换时动态刷新表头与树内容"""
        headers = [
            "",
            t("col_name"),
            t("col_status"),
            t("col_pid"),
            t("col_category"),
            t("col_conns"),
            t("col_path")
        ]
        self.setColumnCount(len(headers))
        self.setHeaderLabels(headers)
        if self.displayed_families:
            self._render_tree()

    def update_data(self, families: list[ProcessFamily]):
        """更新家族列表，保持原有的勾选状态与展开状态"""
        checked_pids = set()
        checked_fams = set()
        expanded_fams = set()

        for fam in self.families_data:
            non_prot = [c for c in fam.children if not c.is_protected]
            if non_prot and all(c.selected for c in non_prot):
                checked_fams.add(fam.family_id)
            for child in fam.children:
                if child.selected and not child.is_protected:
                    checked_pids.add(child.pid)

        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            fam_id = item.data(0, Qt.UserRole)
            if fam_id and item.isExpanded():
                expanded_fams.add(fam_id)

        self.families_data = families

        for fam in self.families_data:
            is_entire_fam_checked = (fam.family_id in checked_fams)
            for child in fam.children:
                if child.is_protected:
                    child.selected = False
                elif is_entire_fam_checked or (child.pid in checked_pids):
                    child.selected = True
                else:
                    child.selected = False

            non_prot = [c for c in fam.children if not c.is_protected]
            fam.selected = bool(non_prot and all(c.selected for c in non_prot))

        self.apply_filter(self.current_search, self.current_filter, expanded_fams)

    def apply_filter(self, search_text: str, category_filter: str, expanded_fams: set = None):
        """根据搜索与分类过滤展示"""
        self.current_search = search_text
        self.current_filter = category_filter
        search_lower = search_text.strip().lower()
        self.displayed_families = []

        for fam in self.families_data:
            # 类别过滤
            if category_filter == "DOWNLOADER" and fam.category != ProcessCategory.DOWNLOADER:
                continue
            elif category_filter == "CLOUD_DRIVE" and fam.category != ProcessCategory.CLOUD_DRIVE:
                continue
            elif category_filter == "GAME" and fam.category != ProcessCategory.GAME:
                continue
            elif category_filter == "BROWSER_SOCIAL" and fam.category != ProcessCategory.BROWSER_SOCIAL:
                continue
            elif category_filter == "LIMITED" and not (fam.is_limited or any(c.is_limited for c in fam.children)):
                continue

            # 搜索文本过滤
            if search_lower:
                match_fam = search_lower in fam.display_name.lower() or search_lower in fam.family_id
                match_child = any(
                    search_lower in c.name.lower() or search_lower in str(c.pid) or search_lower in c.exe_path.lower()
                    for c in fam.children
                )
                if not (match_fam or match_child):
                    continue

            self.displayed_families.append(fam)

        self._render_tree(expanded_fams)

    def _render_tree(self, expanded_fams: set = None):
        self.clear()
        bold_font = QFont()
        bold_font.setBold(True)

        for fam in self.displayed_families:
            fam_item = QTreeWidgetItem(self)
            fam_item.setData(0, Qt.UserRole, fam.family_id)

            # 计算家族初始勾选状态 (三态联动)
            non_prot = [c for c in fam.children if not c.is_protected]
            if not non_prot:
                fam_state = Qt.Unchecked
                fam.selected = False
            elif all(c.selected for c in non_prot):
                fam_state = Qt.Checked
                fam.selected = True
            elif any(c.selected for c in non_prot):
                fam_state = Qt.PartiallyChecked
                fam.selected = False
            else:
                fam_state = Qt.Unchecked
                fam.selected = False

            # 复选框 (Column 0)
            if len(fam.children) > 1:
                cb = TristateHeaderCheckBox()
                cb.setTristate(True)
                cb.setCheckState(fam_state)
            else:
                cb = QCheckBox()
                cb.setChecked(fam_state == Qt.Checked)

            if fam.is_protected:
                cb.setEnabled(False)
                cb.setToolTip(t("protected_tooltip"))
            else:
                cb.stateChanged.connect(lambda state, f=fam, item=fam_item: self._on_family_checkbox_changed(f, item, state))
            self.setItemWidget(fam_item, COL_CHECK, self._wrap_checkbox(cb))

            # 家族名称 (Column 1)
            count_str = t("processes_count", count=len(fam.children)) if len(fam.children) > 1 else ""
            fam_item.setText(COL_NAME, f"{fam.category.icon}  {fam.display_name}{count_str}")
            fam_item.setFont(COL_NAME, bold_font)
            if fam.is_limited:
                fam_item.setForeground(COL_NAME, QColor("#f87171"))

            # 限制状态 (Column 2 - 前置展示)
            disp_summary = format_summary_i18n(fam.limit_summary)
            fam_item.setText(COL_STATUS, disp_summary)
            if fam.is_limited:
                fam_item.setFont(COL_STATUS, bold_font)
                fam_item.setForeground(COL_STATUS, QColor("#fbbf24" if ("KB/s" in fam.limit_summary or "MB/s" in fam.limit_summary) else "#f87171"))
            else:
                fam_item.setForeground(COL_STATUS, QColor("#64748b"))

            # PID (Column 3)
            pid_text = t("total_count", count=len(fam.children)) if len(fam.children) > 1 else str(fam.children[0].pid if fam.children else "")
            fam_item.setText(COL_PID, pid_text)
            fam_item.setTextAlignment(COL_PID, Qt.AlignCenter)
            fam_item.setForeground(COL_PID, QColor("#94a3b8"))

            # 类别 (Column 4 - 支持多语言国际化)
            cat_display = t(f"cat_{fam.category.name}")
            fam_item.setText(COL_CATEGORY, cat_display)
            fam_item.setTextAlignment(COL_CATEGORY, Qt.AlignCenter)
            fam_item.setForeground(COL_CATEGORY, QColor(fam.category.color))

            # 网络连接 (Column 5)
            conn_str = t("conn_units", count=fam.total_connections) if fam.total_connections > 0 else "—"
            fam_item.setText(COL_CONNS, conn_str)
            fam_item.setTextAlignment(COL_CONNS, Qt.AlignCenter)
            if fam.total_connections > 0:
                fam_item.setForeground(COL_CONNS, QColor("#38bdf8"))
            else:
                fam_item.setForeground(COL_CONNS, QColor("#64748b"))

            # 执行文件路径 (Column 6 - 排在最后)
            path_str = fam.children[0].exe_path if fam.children else ""
            fam_item.setText(COL_PATH, path_str)
            fam_item.setToolTip(COL_PATH, path_str)
            fam_item.setForeground(COL_PATH, QColor("#64748b"))

            # 二级详细子进程节点
            if len(fam.children) > 1:
                for child in fam.children:
                    child_item = QTreeWidgetItem(fam_item)
                    child_item.setData(0, Qt.UserRole, child.pid)

                    child_cb = QCheckBox()
                    child_cb.setChecked(child.selected)
                    if child.is_protected:
                        child_cb.setEnabled(False)
                        child_cb.setToolTip(t("protected_tooltip"))
                    else:
                        child_cb.stateChanged.connect(lambda state, c=child, f=fam, p_item=fam_item: self._on_child_checkbox_changed(c, f, p_item, state))
                    self.setItemWidget(child_item, COL_CHECK, self._wrap_checkbox(child_cb))

                    child_item.setText(COL_NAME, f"↳ {child.name}")
                    if child.is_limited:
                        child_item.setForeground(COL_NAME, QColor("#f87171"))

                    c_summary = format_summary_i18n(child.limit_summary)
                    child_item.setText(COL_STATUS, c_summary)
                    if child.is_limited:
                        child_item.setForeground(COL_STATUS, QColor("#fbbf24" if ("KB/s" in child.limit_summary or "MB/s" in child.limit_summary) else "#f87171"))
                    else:
                        child_item.setForeground(COL_STATUS, QColor("#64748b"))

                    child_item.setText(COL_PID, str(child.pid))
                    child_item.setTextAlignment(COL_PID, Qt.AlignCenter)
                    child_item.setForeground(COL_PID, QColor("#cbd5e1"))

                    child_cat = t(f"cat_{child.category.name}")
                    child_item.setText(COL_CATEGORY, child_cat)
                    child_item.setTextAlignment(COL_CATEGORY, Qt.AlignCenter)
                    child_item.setForeground(COL_CATEGORY, QColor(child.category.color))

                    child_conn = t("conn_units", count=child.connections_count) if child.connections_count > 0 else "—"
                    child_item.setText(COL_CONNS, child_conn)
                    child_item.setTextAlignment(COL_CONNS, Qt.AlignCenter)
                    child_item.setForeground(COL_CONNS, QColor("#38bdf8" if child.connections_count > 0 else "#64748b"))

                    child_item.setText(COL_PATH, child.exe_path)
                    child_item.setToolTip(COL_PATH, child.exe_path)
                    child_item.setForeground(COL_PATH, QColor("#94a3b8"))

            if expanded_fams and fam.family_id in expanded_fams:
                fam_item.setExpanded(True)

        self._emit_selected_count()

    def _wrap_checkbox(self, cb: QCheckBox) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.addWidget(cb)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        return container

    def _on_family_checkbox_changed(self, fam: ProcessFamily, fam_item: QTreeWidgetItem, state: int):
        is_checked = (state == Qt.Checked)
        fam.selected = is_checked
        for child in fam.children:
            if not child.is_protected:
                child.selected = is_checked
        for i in range(fam_item.childCount()):
            child_item = fam_item.child(i)
            widget = self.itemWidget(child_item, COL_CHECK)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb and cb.isEnabled():
                    cb.blockSignals(True)
                    cb.setChecked(is_checked)
                    cb.blockSignals(False)
        self._emit_selected_count()

    def _on_child_checkbox_changed(self, child: ProcessItem, fam: ProcessFamily, fam_item: QTreeWidgetItem, state: int):
        child.selected = (state == Qt.Checked)

        non_prot = [c for c in fam.children if not c.is_protected]
        if not non_prot:
            fam.selected = False
            target_state = Qt.Unchecked
        elif all(c.selected for c in non_prot):
            fam.selected = True
            target_state = Qt.Checked
        elif any(c.selected for c in non_prot):
            fam.selected = False
            target_state = Qt.PartiallyChecked
        else:
            fam.selected = False
            target_state = Qt.Unchecked

        fam_widget = self.itemWidget(fam_item, COL_CHECK)
        if fam_widget:
            fam_cb = fam_widget.findChild(QCheckBox)
            if fam_cb:
                fam_cb.blockSignals(True)
                fam_cb.setCheckState(target_state)
                fam_cb.blockSignals(False)
        self._emit_selected_count()

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        widget = self.itemWidget(item, COL_CHECK)
        if widget:
            cb = widget.findChild(QCheckBox)
            if cb and cb.isEnabled():
                cb.nextCheckState()

    def select_all(self, selected: bool):
        # 仅对当前筛选展示的项生效，且自动跳过系统保护进程
        for fam in self.displayed_families:
            if selected and fam.is_protected:
                continue
            for c in fam.children:
                if selected and c.is_protected:
                    continue
                c.selected = selected
            non_prot = [c for c in fam.children if not c.is_protected]
            fam.selected = bool(selected and non_prot and all(c.selected for c in non_prot))
        self._render_tree()

    def invert_selection(self):
        # 仅对当前筛选展示的项生效，且跳过系统保护进程
        for fam in self.displayed_families:
            if fam.is_protected:
                continue
            for c in fam.children:
                if c.is_protected:
                    continue
                c.selected = not c.selected
            non_prot = [c for c in fam.children if not c.is_protected]
            fam.selected = bool(non_prot and all(c.selected for c in non_prot))
        self._render_tree()

    def get_selected_targets(self) -> list[tuple[str, str]]:
        targets = {}
        for fam in self.families_data:
            for child in fam.children:
                if child.is_protected:
                    continue
                if child.selected:
                    name_key = child.name.lower()
                    if name_key not in targets:
                        targets[name_key] = (child.name, child.exe_path)
        return list(targets.values())

    def _emit_selected_count(self):
        targets = self.get_selected_targets()
        self.selectionChangedCustom.emit(len(targets))
