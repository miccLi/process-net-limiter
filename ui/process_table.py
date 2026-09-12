# -*- coding: utf-8 -*-
"""
自定义进程表格组件
支持复选框多选、高亮状态徽章、排序和快捷操作
"""
from PyQt5.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QCheckBox, QWidget, QHBoxLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from core.process_scanner import ProcessItem, ProcessCategory

class ProcessTableWidget(QTableWidget):
    selectionChangedCustom = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items_data: list[ProcessItem] = []
        self.displayed_items: list[ProcessItem] = []
        self._init_ui()

    def _init_ui(self):
        headers = ["", "程序名称", "PID", "类别", "网络连接", "当前限制状态", "执行文件路径"]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.setColumnWidth(0, 42)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        self.setColumnWidth(1, 200)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        self.setColumnWidth(2, 75)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        self.setColumnWidth(3, 110)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        self.setColumnWidth(4, 95)
        header.setSectionResizeMode(5, QHeaderView.Interactive)
        self.setColumnWidth(5, 170)
        header.setSectionResizeMode(6, QHeaderView.Stretch)

        self.cellClicked.connect(self._on_cell_clicked)

    def update_data(self, items: list[ProcessItem]):
        """更新表格数据"""
        # 保留原有勾选状态
        checked_names = {item.name.lower() for item in self.items_data if item.selected}
        self.items_data = items
        for it in self.items_data:
            if it.name.lower() in checked_names:
                it.selected = True

        self.apply_filter("", "ALL")

    def apply_filter(self, search_text: str, category_filter: str):
        """根据搜索文本和类别过滤显示行"""
        search_lower = search_text.strip().lower()
        self.displayed_items = []

        for item in self.items_data:
            # 类别过滤
            if category_filter == "DOWNLOADER" and item.category != ProcessCategory.DOWNLOADER:
                continue
            elif category_filter == "CLOUD_DRIVE" and item.category != ProcessCategory.CLOUD_DRIVE:
                continue
            elif category_filter == "GAME" and item.category != ProcessCategory.GAME:
                continue
            elif category_filter == "LIMITED" and not item.is_limited:
                continue

            # 搜索文本过滤 (按进程名、PID 或路径)
            if search_lower:
                in_name = search_lower in item.name.lower()
                in_pid = search_lower in str(item.pid)
                in_path = search_lower in item.exe_path.lower()
                if not (in_name or in_pid or in_path):
                    continue

            self.displayed_items.append(item)

        self._render_rows()

    def _render_rows(self):
        self.setRowCount(len(self.displayed_items))
        
        bold_font = QFont()
        bold_font.setBold(True)

        for row, item in enumerate(self.displayed_items):
            self.setRowHeight(row, 36)

            # Column 0: Checkbox
            cb = QCheckBox()
            cb.setChecked(item.selected)
            cb.setProperty("row", row)
            cb.stateChanged.connect(lambda state, it=item: self._on_checkbox_changed(it, state))
            
            cb_container = QWidget()
            cb_layout = QHBoxLayout(cb_container)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.setCellWidget(row, 0, cb_container)

            # Column 1: 程序名称
            name_item = QTableWidgetItem(f"{item.category.icon} {item.name}")
            name_item.setFont(bold_font)
            if item.is_limited:
                name_item.setForeground(QColor("#f87171"))  # 红色高亮
            self.setItem(row, 1, name_item)

            # Column 2: PID
            pid_item = QTableWidgetItem(str(item.pid))
            pid_item.setTextAlignment(Qt.AlignCenter)
            pid_item.setForeground(QColor("#94a3b8"))
            self.setItem(row, 2, pid_item)

            # Column 3: 类别
            cat_item = QTableWidgetItem(f"{item.category.display_name}")
            cat_item.setTextAlignment(Qt.AlignCenter)
            cat_item.setForeground(QColor(item.category.color))
            self.setItem(row, 3, cat_item)

            # Column 4: 网络连接
            conn_text = f"{item.connections_count} 个连接" if item.connections_count > 0 else "无活动"
            conn_item = QTableWidgetItem(conn_text)
            conn_item.setTextAlignment(Qt.AlignCenter)
            if item.connections_count > 0:
                conn_item.setForeground(QColor("#38bdf8"))
            else:
                conn_item.setForeground(QColor("#64748b"))
            self.setItem(row, 4, conn_item)

            # Column 5: 当前限制状态
            status_item = QTableWidgetItem(item.limit_summary)
            if item.is_limited:
                status_item.setFont(bold_font)
                status_item.setForeground(QColor("#fbbf24" if "KB/s" in item.limit_summary else "#f87171"))
            else:
                status_item.setForeground(QColor("#64748b"))
            self.setItem(row, 5, status_item)

            # Column 6: 执行文件路径
            path_item = QTableWidgetItem(item.exe_path)
            path_item.setToolTip(item.exe_path)
            path_item.setForeground(QColor("#94a3b8"))
            self.setItem(row, 6, path_item)

        self._emit_selected_count()

    def _on_checkbox_changed(self, item: ProcessItem, state: int):
        item.selected = (state == Qt.Checked)
        self._emit_selected_count()

    def _on_cell_clicked(self, row: int, column: int):
        if 0 <= row < len(self.displayed_items):
            item = self.displayed_items[row]
            item.selected = not item.selected
            # 更新复选框 UI
            cb_widget = self.cellWidget(row, 0)
            if cb_widget:
                cb = cb_widget.findChild(QCheckBox)
                if cb:
                    cb.blockSignals(True)
                    cb.setChecked(item.selected)
                    cb.blockSignals(False)
            self._emit_selected_count()

    def select_all(self, selected: bool):
        for item in self.displayed_items:
            item.selected = selected
        self._render_rows()

    def invert_selection(self):
        for item in self.displayed_items:
            item.selected = not item.selected
        self._render_rows()

    def get_selected_items(self) -> list[ProcessItem]:
        return [item for item in self.items_data if item.selected]

    def _emit_selected_count(self):
        count = sum(1 for it in self.items_data if it.selected)
        self.selectionChangedCustom.emit(count)
