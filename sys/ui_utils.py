# File: ui_utils.py
# Functionality: 提供通用的用户界面元素与样式，确保整个应用程序的界面风格统一

from PyQt5.QtWidgets import QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt

INPUT_STYLE = "padding: 8px 10px; border-radius: 6px; border: 1px solid #ccc; font-size: 14px;"

def styled_line_edit(password=False):
    """Creates a styled QLineEdit, optionally for passwords."""
    le = QLineEdit()
    if password:
        le.setEchoMode(QLineEdit.Password)
    le.setMinimumWidth(320)
    le.setFixedHeight(40)
    le.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    le.setStyleSheet(INPUT_STYLE)
    return le

def styled_button(text, style="default"):
    """Creates a styled QPushButton."""
    btn = QPushButton(text)
    if style == "default":
        btn.setStyleSheet("""
            QPushButton {
                background-color: #5dade2;
                color: white;
                border-radius: 10px;
                padding: 20px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3498db; }
        """)
    elif style == "save":
        btn.setStyleSheet("""
            background-color: #5dade2; color: white; border-radius: 8px; padding: 10px; font-weight: bold;
        """)
    return btn

def create_table(headers, data, editable_columns=None):
    """Creates a QTableWidget with given headers and data. Optionally makes columns editable."""
    table = QTableWidget()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    table.setRowCount(len(data))
    editable_columns = editable_columns or []
    for i, row in enumerate(data):
        for j, item in enumerate(row):
            qitem = QTableWidgetItem(str(item) if item is not None else "")
            if j in editable_columns:
                qitem.setFlags(qitem.flags() | Qt.ItemIsEditable)
            else:
                qitem.setFlags(qitem.flags() & ~Qt.ItemIsEditable)
            table.setItem(i, j, qitem)
    return table