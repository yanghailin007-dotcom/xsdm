#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大文娱小说发布助手 - 现代化样式定义
Material Design 风格
"""

# 主色调定义
PRIMARY_COLOR = "#1976D2"          # 主蓝色
PRIMARY_LIGHT = "#63A4FF"          # 浅蓝
PRIMARY_DARK = "#004BA0"           # 深蓝
ACCENT_COLOR = "#FF4081"           # 强调色（粉红）
SUCCESS_COLOR = "#4CAF50"          # 成功绿
WARNING_COLOR = "#FFC107"          # 警告黄
ERROR_COLOR = "#F44336"            # 错误红
INFO_COLOR = "#2196F3"             # 信息蓝

# 背景色
BG_PRIMARY = "#FAFAFA"             # 主背景
BG_CARD = "#FFFFFF"                # 卡片背景
BG_HOVER = "#F5F5F5"               # 悬停背景

# 文字颜色
TEXT_PRIMARY = "#212121"           # 主文字
TEXT_SECONDARY = "#757575"         # 次要文字
TEXT_DISABLED = "#BDBDBD"          # 禁用文字

# 边框颜色
BORDER_LIGHT = "#E0E0E0"           # 浅色边框
BORDER_MEDIUM = "#BDBDBD"          # 中等边框

# 主窗口样式
MAIN_WINDOW_STYLE = f"""
QMainWindow {{
    background-color: {BG_PRIMARY};
}}
"""

# 分组框样式
group_box_style = f"""
QGroupBox {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    padding-bottom: 12px;
    padding-left: 16px;
    padding-right: 16px;
    font-weight: 600;
    color: {TEXT_PRIMARY};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    color: {PRIMARY_COLOR};
    font-size: 13px;
    font-weight: 700;
}}
"""

# 按钮样式 - 主要按钮
BUTTON_PRIMARY = f"""
QPushButton {{
    background-color: {PRIMARY_COLOR};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 24px;
    font-weight: 600;
    font-size: 13px;
    min-height: 36px;
}}

QPushButton:hover {{
    background-color: {PRIMARY_LIGHT};
}}

QPushButton:pressed {{
    background-color: {PRIMARY_DARK};
}}

QPushButton:disabled {{
    background-color: #BBDEFB;
    color: white;
}}
"""

# 按钮样式 - 成功按钮
BUTTON_SUCCESS = f"""
QPushButton {{
    background-color: {SUCCESS_COLOR};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 24px;
    font-weight: 600;
    font-size: 13px;
    min-height: 36px;
}}

QPushButton:hover {{
    background-color: #66BB6A;
}}

QPushButton:pressed {{
    background-color: #388E3C;
}}

QPushButton:disabled {{
    background-color: #C8E6C9;
}}
"""

# 按钮样式 - 危险/停止按钮
BUTTON_DANGER = f"""
QPushButton {{
    background-color: {ERROR_COLOR};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 24px;
    font-weight: 600;
    font-size: 13px;
    min-height: 36px;
}}

QPushButton:hover {{
    background-color: #EF5350;
}}

QPushButton:pressed {{
    background-color: #D32F2F;
}}
"""

# 按钮样式 - 次要按钮（描边）
BUTTON_SECONDARY = f"""
QPushButton {{
    background-color: transparent;
    color: {PRIMARY_COLOR};
    border: 2px solid {PRIMARY_COLOR};
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: 600;
    font-size: 13px;
    min-height: 32px;
}}

QPushButton:hover {{
    background-color: #E3F2FD;
}}

QPushButton:pressed {{
    background-color: #BBDEFB;
}}
"""

# 下拉框样式
COMBOBOX_STYLE = f"""
QComboBox {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_MEDIUM};
    border-radius: 6px;
    padding: 8px 12px;
    min-height: 20px;
    font-size: 13px;
    color: {TEXT_PRIMARY};
}}

QComboBox:hover {{
    border-color: {PRIMARY_COLOR};
}}

QComboBox:focus {{
    border-color: {PRIMARY_COLOR};
    border-width: 2px;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid {BORDER_LIGHT};
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {TEXT_SECONDARY};
    width: 0;
    height: 0;
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 6px;
    selection-background-color: #E3F2FD;
    selection-color: {PRIMARY_COLOR};
    padding: 4px;
}}
"""

# 列表控件样式
LIST_STYLE = f"""
QListWidget {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 8px;
    padding: 8px;
    font-size: 13px;
    color: {TEXT_PRIMARY};
    outline: none;
}}

QListWidget::item {{
    padding: 10px 12px;
    border-radius: 6px;
    margin: 2px 4px;
}}

QListWidget::item:hover {{
    background-color: {BG_HOVER};
}}

QListWidget::item:selected {{
    background-color: #E3F2FD;
    color: {PRIMARY_COLOR};
    font-weight: 600;
}}

QListWidget::item:checked {{
    background-color: #E8F5E9;
    color: {SUCCESS_COLOR};
}}
"""

# 进度条样式
PROGRESS_STYLE = f"""
QProgressBar {{
    background-color: #E0E0E0;
    border: none;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    font-size: 11px;
    color: {TEXT_PRIMARY};
}}

QProgressBar::chunk {{
    background-color: {PRIMARY_COLOR};
    border-radius: 6px;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 {PRIMARY_COLOR},
        stop: 1 {PRIMARY_LIGHT}
    );
}}

QProgressBar::chunk:disabled {{
    background-color: #BBDEFB;
}}
"""

# 日志文本框样式
LOG_STYLE = f"""
QTextEdit {{
    background-color: #263238;
    color: #EEFFFF;
    border: none;
    border-radius: 8px;
    padding: 12px;
    font-family: "Consolas", "Monaco", "Courier New", monospace;
    font-size: 12px;
    line-height: 1.5;
}}

QTextEdit:focus {{
    border: 2px solid {PRIMARY_LIGHT};
}}
"""

# 标签页样式
TAB_STYLE = f"""
QTabWidget::pane {{
    border: none;
    background-color: transparent;
    top: -1px;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    padding: 12px 20px;
    margin-right: 4px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: 500;
    font-size: 13px;
}}

QTabBar::tab:hover {{
    color: {PRIMARY_COLOR};
    background-color: #E3F2FD;
    border-radius: 6px 6px 0 0;
}}

QTabBar::tab:selected {{
    color: {PRIMARY_COLOR};
    border-bottom: 2px solid {PRIMARY_COLOR};
    font-weight: 600;
}}

QTabBar::tab:!selected {{
    margin-top: 2px;
}}
"""

# 复选框样式
CHECKBOX_STYLE = f"""
QCheckBox {{
    spacing: 8px;
    font-size: 13px;
    color: {TEXT_PRIMARY};
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border: 2px solid {BORDER_MEDIUM};
    border-radius: 4px;
    background-color: {BG_CARD};
}}

QCheckBox::indicator:hover {{
    border-color: {PRIMARY_COLOR};
}}

QCheckBox::indicator:checked {{
    background-color: {PRIMARY_COLOR};
    border-color: {PRIMARY_COLOR};
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNCIgaGVpZ2h0PSIxNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjMiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
}}

QCheckBox::indicator:disabled {{
    background-color: #EEEEEE;
    border-color: #BDBDBD;
}}
"""

# 数字选择器样式
SPINBOX_STYLE = f"""
QSpinBox, QDoubleSpinBox {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_MEDIUM};
    border-radius: 6px;
    padding: 8px;
    font-size: 13px;
    color: {TEXT_PRIMARY};
    min-height: 20px;
}}

QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {PRIMARY_COLOR};
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {PRIMARY_COLOR};
    border-width: 2px;
}}

QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid {BORDER_LIGHT};
    border-top-right-radius: 6px;
}}

QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 24px;
    border-left: 1px solid {BORDER_LIGHT};
    border-bottom-right-radius: 6px;
}}
"""

# 菜单栏样式
MENU_STYLE = f"""
QMenu {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 8px;
    padding: 8px 0;
    margin: 4px;
}}

QMenu::item {{
    padding: 10px 24px;
    font-size: 13px;
    color: {TEXT_PRIMARY};
}}

QMenu::item:hover {{
    background-color: #E3F2FD;
    color: {PRIMARY_COLOR};
}}

QMenu::item:selected {{
    background-color: #E3F2FD;
    color: {PRIMARY_COLOR};
}}

QMenu::separator {{
    height: 1px;
    background-color: {BORDER_LIGHT};
    margin: 8px 16px;
}}
"""

# 状态栏样式
STATUSBAR_STYLE = f"""
QStatusBar {{
    background-color: {BG_CARD};
    color: {TEXT_SECONDARY};
    border-top: 1px solid {BORDER_LIGHT};
    padding: 4px 16px;
    font-size: 12px;
}}

QStatusBar::item {{
    border: none;
}}
"""

# 消息框样式
MESSAGEBOX_STYLE = f"""
QMessageBox {{
    background-color: {BG_CARD};
}}

QMessageBox QLabel {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}

QMessageBox QPushButton {{
    background-color: {PRIMARY_COLOR};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 20px;
    font-weight: 600;
    min-width: 80px;
}}

QMessageBox QPushButton:hover {{
    background-color: {PRIMARY_LIGHT};
}}
"""

# 应用完整样式
def get_application_style():
    """获取完整的应用程序样式"""
    return f"""
    {MAIN_WINDOW_STYLE}
    
    QGroupBox {group_box_style}
    
    QPushButton {{
        background-color: {PRIMARY_COLOR};
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 24px;
        font-weight: 600;
        font-size: 13px;
        min-height: 36px;
    }}
    
    QPushButton:hover {{
        background-color: {PRIMARY_LIGHT};
    }}
    
    QPushButton:pressed {{
        background-color: {PRIMARY_DARK};
    }}
    
    QPushButton:disabled {{
        background-color: #BBDEFB;
        color: white;
    }}
    
    QPushButton[class="secondary"] {BUTTON_SECONDARY}
    
    QPushButton[class="success"] {BUTTON_SUCCESS}
    
    QPushButton[class="danger"] {BUTTON_DANGER}
    
    {COMBOBOX_STYLE}
    
    {LIST_STYLE}
    
    {PROGRESS_STYLE}
    
    {TAB_STYLE}
    
    {CHECKBOX_STYLE}
    
    {SPINBOX_STYLE}
    
    {MENU_STYLE}
    
    {STATUSBAR_STYLE}
    
    {MESSAGEBOX_STYLE}
    
    QTextEdit[readOnly="true"] {LOG_STYLE}
    
    QLabel {{
        color: {TEXT_PRIMARY};
        font-size: 13px;
    }}
    
    QSplitter::handle {{
        background-color: {BORDER_LIGHT};
    }}
    
    QSplitter::handle:horizontal {{
        width: 2px;
    }}
    
    QSplitter::handle:hover {{
        background-color: {PRIMARY_LIGHT};
    }}
    """


# 卡片组件样式
def card_style():
    """获取卡片样式"""
    return f"""
    background-color: {BG_CARD};
    border: 1px solid {BORDER_LIGHT};
    border-radius: 12px;
    padding: 20px;
    """


# 标题样式
def header_style(size="medium"):
    """获取标题样式"""
    sizes = {
        "large": "24px",
        "medium": "18px",
        "small": "14px"
    }
    return f"""
    color: {TEXT_PRIMARY};
    font-size: {sizes.get(size, '16px')};
    font-weight: 700;
    """


# 次要文字样式
def text_secondary_style():
    """获取次要文字样式"""
    return f"""
    color: {TEXT_SECONDARY};
    font-size: 12px;
    """
