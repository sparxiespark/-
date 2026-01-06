# File: main.py
# Functionality: 应用程序的入口点。负责初始化 QApplication 并显示登录窗口
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont

from login_window import LoginWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())