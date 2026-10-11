# -*- coding: utf-8 -*-
"""
现代化暗色质感主题 (Sleek Modern Fluent & Glassmorphism Theme)
针对高分屏 (High-DPI)、Windows 10/11 视觉规范与现代桌面美学全面深度重构。
"""

DARK_THEME_QSS = """
/* 浮动提示框 ToolTip 样式优化 */
QToolTip {
    background-color: #1a2230;
    color: #f8fafc;
    border: 1px solid #3b4d66;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
    font-family: "Segoe UI Variable Text", "Segoe UI", "Microsoft YaHei", sans-serif;
}

/* 全局基础设置 */
* {
    font-family: "Segoe UI Variable Text", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 13px;
    color: #e2e8f0;
    outline: none;
}

QMainWindow, QDialog {
    background-color: #0b0f17;
}

QWidget#CentralWidget {
    background-color: #0b0f17;
}

/* 顶部与底部状态面板卡片 */
QFrame#HeaderCard, QFrame#ControlCard {
    background-color: #141b26;
    border: 1px solid #243042;
    border-radius: 12px;
}

/* 标题与子标题标签 */
QLabel#AppTitle {
    font-size: 19px;
    font-weight: 700;
    color: #38bdf8;
    letter-spacing: 0.5px;
}

QLabel#SubTitle {
    font-size: 12px;
    color: #94a3b8;
    padding-left: 4px;
}

QLabel#SectionTitle {
    font-size: 14px;
    font-weight: 700;
    color: #f1f5f9;
}

QLabel#SubText {
    font-size: 12px;
    color: #94a3b8;
}

/* 徽章按钮：管理员权限指示 */
QPushButton#AdminBadgeOk {
    background-color: #064e3b;
    border: 1px solid #10b981;
    color: #34d399;
    font-weight: 600;
    font-size: 12px;
    border-radius: 14px;
    padding: 4px 12px;
}

QPushButton#AdminBadgeWarn {
    background-color: #451a03;
    border: 1px solid #d97706;
    color: #fcd34d;
    font-weight: 600;
    font-size: 12px;
    border-radius: 14px;
    padding: 4px 12px;
}
QPushButton#AdminBadgeWarn:hover {
    background-color: #78350f;
    border-color: #f59e0b;
}

/* 引擎架构状态指示徽章 */
QLabel#EngineBadge {
    border-radius: 14px;
    font-weight: 700;
    font-size: 11px;
    padding: 4px 12px;
}

/* 全局实时吞吐监控徽章 */
QLabel#TrafficBadge {
    background-color: #0f172a;
    border: 1px solid #0284c7;
    border-radius: 14px;
    font-weight: 700;
    font-size: 12px;
    padding: 4px 14px;
    color: #38bdf8;
    letter-spacing: 0.5px;
}


/* 语言切换器选择框 */
QComboBox#LangSelector {
    background-color: #1a2332;
    border: 1px solid #2d3d54;
    border-radius: 14px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
    color: #cbd5e1;
}
QComboBox#LangSelector:hover {
    background-color: #243044;
    border-color: #38bdf8;
    color: #ffffff;
}

/* 搜索输入框 */
QLineEdit {
    background-color: #141b26;
    border: 1px solid #28374d;
    border-radius: 8px;
    padding: 7px 12px;
    color: #f8fafc;
    font-size: 13px;
    selection-background-color: #2563eb;
}
QLineEdit:hover {
    border: 1px solid #3b4d66;
    background-color: #182130;
}
QLineEdit:focus {
    border: 1px solid #38bdf8;
    background-color: #1a2433;
}

/* 下拉选择框 */
QComboBox {
    background-color: #161e2a;
    border: 1px solid #28374d;
    border-radius: 7px;
    padding: 6px 10px;
    min-height: 22px;
    color: #f1f5f9;
}
QComboBox:hover {
    border: 1px solid #3b4d66;
    background-color: #1c2636;
}
QComboBox:focus {
    border: 1px solid #38bdf8;
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}
QComboBox QAbstractItemView {
    background-color: #141b26;
    border: 1px solid #28374d;
    border-radius: 6px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
    color: #f1f5f9;
    padding: 4px;
    outline: none;
}

/* 数字调节框 */
QDoubleSpinBox, QSpinBox {
    background-color: #161e2a;
    border: 1px solid #28374d;
    border-radius: 7px;
    padding: 5px 8px;
    color: #f8fafc;
}
QDoubleSpinBox:hover, QSpinBox:hover {
    border: 1px solid #3b4d66;
    background-color: #1c2636;
}
QDoubleSpinBox:focus, QSpinBox:focus {
    border: 1px solid #38bdf8;
}

/* 复选框 - 高清适配与现代化微交互 */
QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #161e2a;
}
QCheckBox::indicator:hover {
    border-color: #38bdf8;
    background-color: #1c2636;
}
QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #38bdf8;
    image: none;
}
QCheckBox::indicator:indeterminate {
    background-color: #0284c7;
    border-color: #38bdf8;
}

/* 按钮通用设计 */
QPushButton {
    background-color: #1a2332;
    border: 1px solid #2e3e54;
    border-radius: 7px;
    padding: 6px 14px;
    font-weight: 600;
    color: #e2e8f0;
}
QPushButton:hover {
    background-color: #232f42;
    border-color: #3f5473;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #141c29;
}
QPushButton:disabled {
    background-color: #121720;
    border-color: #1e2633;
    color: #64748b;
}

/* 重点操作按钮：应用限速 (Electric Blue to Cyan Gradient) */
QPushButton#ApplyBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #0284c7);
    border: 1px solid #38bdf8;
    color: #ffffff;
    font-weight: 700;
    padding: 8px 20px;
    border-radius: 8px;
    font-size: 13px;
}
QPushButton#ApplyBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #0ea5e9);
    border-color: #7dd3fc;
}
QPushButton#ApplyBtn:pressed {
    background: #1d4ed8;
}
QPushButton#ApplyBtn:disabled {
    background: #1e293b;
    border-color: #334155;
    color: #64748b;
}

/* 危险操作按钮：一键清除所有限制 (Deep Crimson) */
QPushButton#ResetAllBtn {
    background-color: #3b1212;
    border: 1px solid #991b1b;
    color: #fca5a5;
    font-weight: 600;
    padding: 7px 15px;
    border-radius: 7px;
}
QPushButton#ResetAllBtn:hover {
    background-color: #7f1d1d;
    border-color: #ef4444;
    color: #ffffff;
}
QPushButton#ResetAllBtn:pressed {
    background-color: #991b1b;
}

/* 过滤芯片 (Pill-shaped Filter Chips) */
QPushButton#FilterChip {
    background-color: #141b26;
    border: 1px solid #28374d;
    border-radius: 15px;
    padding: 5px 14px;
    font-size: 12px;
    font-weight: 500;
    color: #94a3b8;
}
QPushButton#FilterChip:hover {
    background-color: #1c2535;
    border-color: #3b4d66;
    color: #f1f5f9;
}
QPushButton#FilterChip:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #2563eb);
    border: 1px solid #60a5fa;
    color: #ffffff;
    font-weight: 700;
}
QPushButton#FilterChip:checked:hover {
    background: #2563eb;
    border-color: #93c5fd;
    color: #ffffff;
}

/* 树状组件样式 (QTreeWidget - 现代任务管理器卡片风格) */
QTreeWidget {
    background-color: #111722;
    alternate-background-color: #141b26;
    border: 1px solid #243042;
    border-radius: 10px;
    selection-background-color: #1e3a8a;
    selection-color: #ffffff;
    padding: 4px;
}
QTreeWidget::item {
    height: 34px;
    border-bottom: 1px solid #192230;
    border-radius: 4px;
    padding: 2px 4px;
}
QTreeWidget::item:hover {
    background-color: #1c2738;
}
QTreeWidget::item:selected {
    background-color: #1e3a8a;
    color: #ffffff;
}
QTreeWidget::branch:has-children:!has-siblings:closed,
QTreeWidget::branch:closed:has-children:has-siblings {
    image: none;
    border-image: none;
}

QHeaderView::section {
    background-color: #141b26;
    color: #94a3b8;
    font-weight: 700;
    font-size: 12px;
    padding: 7px 6px;
    border: none;
    border-bottom: 2px solid #28374d;
}

/* 底部机制提示卡片 (Tip Banner) */
QFrame#TipBanner {
    background-color: #121a24;
    border: 1px solid #223042;
    border-left: 3px solid #38bdf8;
    border-radius: 6px;
    padding: 6px 10px;
}

/* 滚动条 */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #2b394e;
    min-height: 25px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #3b4d66;
}
QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 8px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: #2b394e;
    min-width: 25px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #3b4d66;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0px;
    height: 0px;
}
QScrollBar::add-page, QScrollBar::sub-page {
    background: none;
}

/* 状态栏 */
QStatusBar {
    background-color: #0b0f17;
    color: #8191a6;
    font-size: 12px;
    border-top: 1px solid #1a2230;
    padding: 3px 6px;
}
"""
