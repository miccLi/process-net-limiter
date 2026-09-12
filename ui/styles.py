# -*- coding: utf-8 -*-
"""
现代化暗色质感主题 (Sleek Modern Dark Glassmorphism)
"""

DARK_THEME_QSS = """
/* 浮动提示框 ToolTip 样式优化 (深色背景，清晰文字) */
QToolTip {
    background-color: #1e242d;
    color: #f8fafc;
    border: 1px solid #475569;
    border-radius: 4px;
    padding: 5px 9px;
    font-size: 12px;
}

/* 全局基础设置 */
* {
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
    color: #f1f5f9;
}

QMainWindow, QDialog {
    background-color: #0f1217;
}

QWidget#CentralWidget {
    background-color: #0f1217;
}

/* 顶部与底部状态面板卡片 */
QFrame#HeaderCard, QFrame#ControlCard {
    background-color: #171b22;
    border: 1px solid #28303d;
    border-radius: 10px;
}

/* 标题标签 */
QLabel#AppTitle {
    font-size: 18px;
    font-weight: bold;
    color: #60a5fa;
}

QLabel#SectionTitle {
    font-size: 14px;
    font-weight: bold;
    color: #e2e8f0;
}

QLabel#SubText {
    font-size: 12px;
    color: #94a3b8;
}

/* 管理员状态徽章按钮 */
QPushButton#AdminBadgeOk {
    background-color: #064e3b;
    border: 1px solid #10b981;
    color: #34d399;
    font-weight: 600;
    font-size: 12px;
    border-radius: 6px;
    padding: 4px 10px;
}

QPushButton#AdminBadgeWarn {
    background-color: #78350f;
    border: 1px solid #f59e0b;
    color: #fbbf24;
    font-weight: 600;
    font-size: 12px;
    border-radius: 6px;
    padding: 4px 10px;
}
QPushButton#AdminBadgeWarn:hover {
    background-color: #92400e;
    border-color: #fbbf24;
}

/* 搜索输入框 */
QLineEdit {
    background-color: #1e242d;
    border: 1px solid #333d4b;
    border-radius: 6px;
    padding: 6px 12px;
    color: #f8fafc;
    selection-background-color: #3b82f6;
}
QLineEdit:focus {
    border: 1px solid #60a5fa;
    background-color: #242c38;
}

/* 下拉框 */
QComboBox {
    background-color: #1e242d;
    border: 1px solid #333d4b;
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 20px;
    color: #f1f5f9;
}
QComboBox:hover {
    border: 1px solid #4f5d73;
}
QComboBox:focus {
    border: 1px solid #3b82f6;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #171b22;
    border: 1px solid #333d4b;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    color: #f1f5f9;
    padding: 4px;
}

/* 数字调节框 */
QDoubleSpinBox, QSpinBox {
    background-color: #1e242d;
    border: 1px solid #333d4b;
    border-radius: 6px;
    padding: 5px 8px;
    color: #f8fafc;
}
QDoubleSpinBox:focus, QSpinBox:focus {
    border: 1px solid #3b82f6;
}

/* 复选框 */
QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #1e242d;
}
QCheckBox::indicator:hover {
    border-color: #60a5fa;
}
QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #3b82f6;
    image: url(""); /* Qt 默认绘制勾选 */
}

/* 按钮通用设计 */
QPushButton {
    background-color: #242c38;
    border: 1px solid #3b4657;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
    color: #f1f5f9;
}
QPushButton:hover {
    background-color: #313c4c;
    border-color: #4f5d73;
}
QPushButton:pressed {
    background-color: #1a2028;
}

/* 重点操作按钮：应用限速 */
QPushButton#ApplyBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #0284c7);
    border: none;
    color: #ffffff;
    font-weight: bold;
    padding: 8px 18px;
    border-radius: 6px;
}
QPushButton#ApplyBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #0ea5e9);
}
QPushButton#ApplyBtn:pressed {
    background: #1d4ed8;
}

/* 危险操作按钮：一键清除所有限制 */
QPushButton#ResetAllBtn {
    background-color: #451a1a;
    border: 1px solid #991b1b;
    color: #fca5a5;
    font-weight: bold;
    padding: 8px 16px;
    border-radius: 6px;
}
QPushButton#ResetAllBtn:hover {
    background-color: #7f1d1d;
    border-color: #ef4444;
    color: #ffffff;
}
QPushButton#ResetAllBtn:pressed {
    background-color: #991b1b;
}

/* 过滤标签按钮 */
QPushButton#FilterChip {
    background-color: #171b22;
    border: 1px solid #28303d;
    border-radius: 15px;
    padding: 5px 14px;
    font-size: 12px;
    color: #94a3b8;
}
QPushButton#FilterChip:hover {
    background-color: #242c38;
    border-color: #3b4657;
    color: #f1f5f9;
}
QPushButton#FilterChip:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #2563eb);
    border: 1px solid #60a5fa;
    color: #ffffff;
    font-weight: bold;
}
QPushButton#FilterChip:checked:hover {
    background: #3b82f6;
    border-color: #93c5fd;
    color: #ffffff;
}

/* 表格组件 */
QTableWidget {
    background-color: #13171d;
    alternate-background-color: #171c23;
    border: 1px solid #28303d;
    border-radius: 8px;
    gridline-color: #212732;
    selection-background-color: #1e3a8a;
    selection-color: #ffffff;
}
QHeaderView::section {
    background-color: #171b22;
    color: #94a3b8;
    font-weight: 600;
    padding: 6px;
    border: none;
    border-bottom: 2px solid #28303d;
}
QTableCornerButton::section {
    background-color: #171b22;
    border: none;
}

/* 滚动条 */
QScrollBar:vertical {
    border: none;
    background: #0f1217;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #333d4b;
    min-height: 25px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
