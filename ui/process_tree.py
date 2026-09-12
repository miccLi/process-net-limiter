# -*- coding: utf-8 -*-
"""
多级进程家族树组件 (ProcessTreeWidget - 轻量丝滑版)
类似 Windows 任务管理器的折叠树状结构：
- 第一级：进程家族 (聚合总连接数与限速状态，支持折叠展开)
- 第二级：家族子进程 (展示具体 PID 与执行文件路径)
- 清爽高效的列排布：复选框 -> 程序名称 -> 限制状态 (醒目前置) -> PID -> 类别 -> 网络连接 -> 执行文件路径 (排最后)
- 性能极致优化，无冗余轮询，响应秒级即达
"""
from PyQt5.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QHeaderView, QAbstractItemView, QCheckBox, QWidget, QHBoxLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from core.process_scanner import ProcessFamily, ProcessItem, ProcessCategory

# 列定义：将最有用的信息排在前面，路径排在最右侧
COL_CHECK = 0       # 复选框
COL_NAME = 1        # 程序名称 / 进程家族
COL_STATUS = 2      # 当前限制状态 (前置核心列)
COL_PID = 3         # PID
COL_CATEGORY = 4    # 类别徽章
COL_CONNS = 5       # 网络连接
COL_PATH = 6        # 执行文件路径 (排在最后)

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
        headers = [
            "",
            "程序名称 / 进程家族",
            "当前限制状态",
            "PID",
            "类别",
            "网络连接",
            "执行文件路径"
        ]
        self.setColumnCount(len(headers))
        self.setHeaderLabels(headers)

        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setRootIsDecorated(True)
        self.setAnimated(True)

        header = self.header()
        header.setSectionResizeMode(COL_CHECK, QHeaderView.Fixed)
        self.setColumnWidth(COL_CHECK, 42)
        header.setSectionResizeMode(COL_NAME, QHeaderView.Interactive)
        self.setColumnWidth(COL_NAME, 260)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.Interactive)
        self.setColumnWidth(COL_STATUS, 160)
        header.setSectionResizeMode(COL_PID, QHeaderView.Interactive)
        self.setColumnWidth(COL_PID, 80)
        header.setSectionResizeMode(COL_CATEGORY, QHeaderView.Interactive)
        self.setColumnWidth(COL_CATEGORY, 110)
        header.setSectionResizeMode(COL_CONNS, QHeaderView.Interactive)
        self.setColumnWidth(COL_CONNS, 95)
        header.setSectionResizeMode(COL_PATH, QHeaderView.Stretch)

        self.itemClicked.connect(self._on_item_clicked)

    def update_data(self, families: list[ProcessFamily]):
        """更新家族列表，保持原有的勾选状态与展开状态"""
        checked_pids = set()
        checked_fams = set()
        expanded_fams = set()

        for fam in self.families_data:
            if fam.selected:
                checked_fams.add(fam.family_id)
            for child in fam.children:
                if child.selected:
                    checked_pids.add(child.pid)

        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            fam_id = item.data(0, Qt.UserRole)
            if fam_id and item.isExpanded():
                expanded_fams.add(fam_id)

        self.families_data = families

        for fam in self.families_data:
            fam.selected = (fam.family_id in checked_fams)
            for child in fam.children:
                if child.pid in checked_pids or fam.selected:
                    child.selected = True

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
            elif category_filter == "LIMITED" and not fam.is_limited:
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

            # 复选框 (Column 0)
            cb = QCheckBox()
            cb.setChecked(fam.selected)
            cb.stateChanged.connect(lambda state, f=fam, item=fam_item: self._on_family_checkbox_changed(f, item, state))
            self.setItemWidget(fam_item, COL_CHECK, self._wrap_checkbox(cb))

            # 家族名称 (Column 1)
            count_str = f" ({len(fam.children)} 个进程)" if len(fam.children) > 1 else ""
            fam_item.setText(COL_NAME, f"{fam.category.icon} {fam.display_name}{count_str}")
            fam_item.setFont(COL_NAME, bold_font)
            if fam.is_limited:
                fam_item.setForeground(COL_NAME, QColor("#f87171"))

            # 限制状态 (Column 2 - 前置展示)
            fam_item.setText(COL_STATUS, fam.limit_summary)
            if fam.is_limited:
                fam_item.setFont(COL_STATUS, bold_font)
                fam_item.setForeground(COL_STATUS, QColor("#fbbf24" if "KB/s" in fam.limit_summary else "#f87171"))
            else:
                fam_item.setForeground(COL_STATUS, QColor("#64748b"))

            # PID (Column 3)
            pid_text = f"共 {len(fam.children)}" if len(fam.children) > 1 else str(fam.children[0].pid if fam.children else "")
            fam_item.setText(COL_PID, pid_text)
            fam_item.setTextAlignment(COL_PID, Qt.AlignCenter)
            fam_item.setForeground(COL_PID, QColor("#94a3b8"))

            # 类别 (Column 4)
            fam_item.setText(COL_CATEGORY, fam.category.display_name)
            fam_item.setTextAlignment(COL_CATEGORY, Qt.AlignCenter)
            fam_item.setForeground(COL_CATEGORY, QColor(fam.category.color))

            # 网络连接 (Column 5)
            conn_str = f"{fam.total_connections} 个" if fam.total_connections > 0 else "—"
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
                    child_cb.stateChanged.connect(lambda state, c=child, f=fam, p_item=fam_item: self._on_child_checkbox_changed(c, f, p_item, state))
                    self.setItemWidget(child_item, COL_CHECK, self._wrap_checkbox(child_cb))

                    child_item.setText(COL_NAME, f"↳ {child.name}")
                    if child.is_limited:
                        child_item.setForeground(COL_NAME, QColor("#f87171"))

                    child_item.setText(COL_STATUS, child.limit_summary)
                    if child.is_limited:
                        child_item.setForeground(COL_STATUS, QColor("#fbbf24" if "KB/s" in child.limit_summary else "#f87171"))
                    else:
                        child_item.setForeground(COL_STATUS, QColor("#64748b"))

                    child_item.setText(COL_PID, str(child.pid))
                    child_item.setTextAlignment(COL_PID, Qt.AlignCenter)
                    child_item.setForeground(COL_PID, QColor("#cbd5e1"))

                    child_item.setText(COL_CATEGORY, child.category.display_name)
                    child_item.setTextAlignment(COL_CATEGORY, Qt.AlignCenter)
                    child_item.setForeground(COL_CATEGORY, QColor(child.category.color))

                    child_conn = f"{child.connections_count} 个" if child.connections_count > 0 else "—"
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
            child.selected = is_checked
        for i in range(fam_item.childCount()):
            child_item = fam_item.child(i)
            widget = self.itemWidget(child_item, COL_CHECK)
            if widget:
                cb = widget.findChild(QCheckBox)
                if cb:
                    cb.blockSignals(True)
                    cb.setChecked(is_checked)
                    cb.blockSignals(False)
        self._emit_selected_count()

    def _on_child_checkbox_changed(self, child: ProcessItem, fam: ProcessFamily, fam_item: QTreeWidgetItem, state: int):
        child.selected = (state == Qt.Checked)
        fam.selected = any(c.selected for c in fam.children)

        fam_widget = self.itemWidget(fam_item, COL_CHECK)
        if fam_widget:
            fam_cb = fam_widget.findChild(QCheckBox)
            if fam_cb:
                fam_cb.blockSignals(True)
                fam_cb.setChecked(fam.selected)
                fam_cb.blockSignals(False)
        self._emit_selected_count()

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        widget = self.itemWidget(item, COL_CHECK)
        if widget:
            cb = widget.findChild(QCheckBox)
            if cb:
                cb.setChecked(not cb.isChecked())

    def select_all(self, selected: bool):
        for fam in self.families_data:
            fam.selected = selected
            for c in fam.children:
                c.selected = selected
        self._render_tree()

    def invert_selection(self):
        for fam in self.families_data:
            fam.selected = not fam.selected
            for c in fam.children:
                c.selected = not c.selected
        self._render_tree()

    def get_selected_targets(self) -> list[tuple[str, str]]:
        targets = {}
        for fam in self.families_data:
            for child in fam.children:
                if child.selected or fam.selected:
                    name_key = child.name.lower()
                    if name_key not in targets:
                        targets[name_key] = (child.name, child.exe_path)
        return list(targets.values())

    def _emit_selected_count(self):
        count = sum(1 for f in self.families_data if f.selected or any(c.selected for c in f.children))
        self.selectionChangedCustom.emit(count)
