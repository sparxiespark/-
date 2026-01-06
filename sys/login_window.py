# File: login_window.py
# Functionality: 负责登录窗口的管理、用户身份验证，以及登录成功后向主窗口的跳转。

from db_utils import (
    USER_TABLE,
    USERNAME_COLUMN,
    USERID_COLUMN,
    PASSWORD_COLUMN, 
    USERTYPE_COLUMN
)
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QMessageBox

from ui_utils import styled_line_edit, styled_button
from db_utils import db_query_one
from main_window import MainWindow

class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("中国地质大学（武汉）学生管理系统")
        self.setFixedSize(460, 300)
        self.setStyleSheet("background-color: #f0f0f0;")

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(28)
        central_widget.setLayout(layout)

        self.user_input = styled_line_edit()
        self.pass_input = styled_line_edit(password=True)

        layout.addWidget(QLabel("用户名"))
        layout.addWidget(self.user_input)
        layout.addWidget(QLabel("密码"))
        layout.addWidget(self.pass_input)

        self.login_btn = styled_button("登录")
        self.login_btn.clicked.connect(self.check_login)
        layout.addWidget(self.login_btn)

    def check_login(self):
        username = self.user_input.text().strip()
        password = self.pass_input.text()

        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入用户名和密码。")
            return

        try:
            query = f"SELECT {PASSWORD_COLUMN}, {USERTYPE_COLUMN}, {USERID_COLUMN} FROM {USER_TABLE} WHERE {USERNAME_COLUMN} = ?"
            row = db_query_one(query, (username,))
            if row and str(row[0]) == password:
                user_type = row[1]
                user_id = row[2]
                student_id = None
                if user_type == "Student":
                    stu = db_query_one("SELECT StudentID FROM Student WHERE UserID = ?", (user_id,))
                    student_id = stu[0] if stu else None
                self.main_window = MainWindow(user_type=user_type, student_id=student_id, user_id=user_id)
                self.main_window.show()
                self.close()
            else:
                QMessageBox.warning(self, "错误", "用户名或密码错误！")
        except Exception as e:
            QMessageBox.critical(self, "数据库错误", f"无法连接到数据库或查询失败：\n{e}")