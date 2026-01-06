# File: main_window.py
# Functionality: 管理应用主窗口，该窗口包含多个功能标签页，涵盖班级状态、平均学分绩点、课程信息、成绩管理、选课操作、课表导出及校园地图等功能。
# File: main_window.py
import csv
from functools import partial
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QMessageBox, QComboBox, QPushButton, QLabel, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QHBoxLayout)
from PyQt5.QtCore import Qt

from ui_utils import create_table, styled_button
from db_utils import db_execute_many, db_query_all, db_execute, db_query_one
from map_widget import MapWidget

class MainWindow(QMainWindow):
    def __init__(self, user_type="Student", student_id=None, user_id=None):
        super().__init__()
        self.user_type = user_type
        self.student_id = student_id
        self.user_id = user_id
        self.setWindowTitle("中国地质大学（武汉）学生管理系统")
        self.resize(1000, 700)

        # 获取学生性别 (用于导航逻辑)
        self.student_gender = "Male"  # 默认值
        if self.student_id:
            try:
                # 假设 Student 表有 Gender 字段
                row = db_query_one("SELECT Gender FROM Student WHERE StudentID = ?", (self.student_id,))
                if row:
                    self.student_gender = row[0]
            except Exception as e:
                print(f"加载性别失败 (将默认使用Male路径): {e}")

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.create_class_status_tab()
        self.create_gpa_tab()
        self.create_course_overview_tab()
        
        if self.user_type in ("Teacher", "Admin"):
            self.create_grade_manage_tab()
            
        if self.user_type == "Student":
            self.create_course_selection_tab()
            self.create_schedule_export_tab()
        
        # 地图 Tab 必须初始化
        self.create_map_tab()

    def create_class_status_tab(self):
        headers = ["ClassID", "ClassName", "DepartmentName", "人数", "平均成绩", "及格率"]
        try:
            rows = db_query_all(
                """
                SELECT c.ClassID, c.ClassName, d.DeptName, COUNT(DISTINCT s.StudentID) AS StudentCount,
                       AVG(g.Grade) AS AvgScore,
                       CASE WHEN COUNT(g.StudentID) = 0 THEN 0
                            ELSE CAST(100.0 * SUM(CASE WHEN g.Grade >= 60 THEN 1 ELSE 0 END) / COUNT(g.StudentID) AS INT)
                       END AS PassRate
                FROM Class c LEFT JOIN Department d ON c.DeptID = d.DeptID
                             LEFT JOIN Student s ON s.ClassID = c.ClassID
                             LEFT JOIN Grade g ON g.StudentID = s.StudentID
                GROUP BY c.ClassID, c.ClassName, d.DeptName
                """
            )
            data = [list(row) for row in rows]
        except Exception as e:
            QMessageBox.critical(self, "数据库错误", f"查询班级情况失败：\n{e}")
            data = []
        table = create_table(headers, data)
        self.tabs.addTab(table, "班级情况")

    def create_gpa_tab(self):
        headers = ["DeptID", "系名称", "学生ID", "学生姓名", "班级", "总绩点", "平均分"]
        try:
            if self.user_type == "Student" and self.student_id:
                rows = db_query_all(
                    """
                    SELECT d.DeptID, d.DeptName, s.StudentID, s.StudentName, c.ClassName, ISNULL(s.TotalGPA, 0) AS TotalGPA,
                           ISNULL(AVG(g.Grade), 0) AS AvgGrade
                    FROM Student s INNER JOIN Class c ON s.ClassID = c.ClassID
                                   INNER JOIN Department d ON c.DeptID = d.DeptID
                                   LEFT JOIN Grade g ON g.StudentID = s.StudentID
                    WHERE s.StudentID = ?
                    GROUP BY d.DeptID, d.DeptName, s.StudentID, s.StudentName, c.ClassName, s.TotalGPA
                    """,
                    (self.student_id,)
                )
            else:
                rows = db_query_all(
                    """
                    SELECT d.DeptID, d.DeptName, s.StudentID, s.StudentName, c.ClassName, ISNULL(s.TotalGPA, 0) AS TotalGPA,
                           ISNULL(AVG(g.Grade), 0) AS AvgGrade
                    FROM Student s INNER JOIN Class c ON s.ClassID = c.ClassID
                                   INNER JOIN Department d ON c.DeptID = d.DeptID
                                   LEFT JOIN Grade g ON g.StudentID = s.StudentID
                    GROUP BY d.DeptID, d.DeptName, s.StudentID, s.StudentName, c.ClassName, s.TotalGPA
                    """
                )
            data = [list(row) for row in rows]
        except Exception as e:
            QMessageBox.critical(self, "数据库错误", f"查询学生绩点失败：\n{e}")
            data = []
        table = create_table(headers, data)
        self.tabs.addTab(table, "学生绩点")

    def create_course_overview_tab(self):
        headers = ["CourseID", "CourseName", "选课人数", "平均分", "及格率", "重修人数"]
        try:
            rows = db_query_all(
                """
                SELECT c.CourseID, c.CourseName, COUNT(DISTINCT sc.StudentID) AS StudentCount,
                       AVG(g.Grade) AS AvgScore,
                       CASE WHEN COUNT(g.StudentID) = 0 THEN 0
                            ELSE CAST(100.0 * SUM(CASE WHEN g.Grade >= 60 THEN 1 ELSE 0 END) / COUNT(g.StudentID) AS INT)
                       END AS PassRate,
                       SUM(CASE WHEN g.Grade < 60 THEN 1 ELSE 0 END) AS RetakeCount
                FROM Course c LEFT JOIN StudentCourse sc ON sc.CourseID = c.CourseID
                              LEFT JOIN Grade g ON g.CourseID = c.CourseID AND g.StudentID = sc.StudentID
                GROUP BY c.CourseID, c.CourseName
                """
            )
            data = [list(row) for row in rows]
        except Exception as e:
            QMessageBox.critical(self, "数据库错误", f"查询选课总览失败：\n{e}")
            data = []
        table = create_table(headers, data)
        self.tabs.addTab(table, "选课总览")

    # --- 成绩管理部分  -
    def create_grade_manage_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        # 初始化表格
        headers = ["StudentID", "StudentName", "CourseID", "CourseName", "Grade", "Point"]
        self.grade_table = create_table(headers, [], editable_columns=[4, 5])
        layout.addWidget(self.grade_table)

        # 加载数据
        self.load_grade_data()

        save_btn = styled_button("保存修改并刷新绩点", style="save")
        save_btn.clicked.connect(self.save_grade_changes)
        layout.addWidget(save_btn)

        self.tabs.addTab(tab, "成绩管理")

    def load_grade_data(self):
        """单独提取加载数据的逻辑，以便刷新"""
        try:
            rows = db_query_all(
                """
                SELECT g.StudentID, s.StudentName, g.CourseID, c.CourseName, g.Grade, g.Point
                FROM Grade g LEFT JOIN Student s ON s.StudentID = g.StudentID
                             LEFT JOIN Course c ON c.CourseID = g.CourseID
                """
            )
            data = [list(row) for row in rows]
            
            # 更新表格内容
            self.grade_table.setRowCount(len(data))
            editable_columns = [4, 5]
            for i, row in enumerate(data):
                for j, item in enumerate(row):
                    qitem = QTableWidgetItem(str(item) if item is not None else "")
                    if j in editable_columns:
                        qitem.setFlags(qitem.flags() | Qt.ItemIsEditable)
                    else:
                        qitem.setFlags(qitem.flags() & ~Qt.ItemIsEditable)
                    self.grade_table.setItem(i, j, qitem)
        except Exception as e:
            QMessageBox.critical(self, "数据库错误", f"加载成绩失败：\n{e}")

    def save_grade_changes(self):
        row_count = self.grade_table.rowCount()
        if row_count == 0:
            return
        
        params_list = []
        affected_students = set()

        for i in range(row_count):
            student_id = self.grade_table.item(i, 0).text().strip()
            course_id = self.grade_table.item(i, 2).text().strip()
            grade_text = self.grade_table.item(i, 4).text().strip()
            point_text = self.grade_table.item(i, 5).text().strip()
            
            if not student_id or not course_id:
                continue
            try:
                grade_val = float(grade_text) if grade_text else None
                point_val = float(point_text) if point_text else None
                params_list.append((grade_val, point_val, student_id, course_id))
                affected_students.add(student_id)
            except ValueError:
                QMessageBox.warning(self, "格式错误", f"第 {i+1} 行的成绩/绩点格式不正确")
                continue

        if params_list:
            try:
                # 1. 批量更新 Grade 表
                db_execute_many(
                    "UPDATE Grade SET Grade = ?, Point = ? WHERE StudentID = ? AND CourseID = ?",
                    params_list
                )

                # 2. 重新计算并更新受影响学生的 TotalGPA
                # 逻辑：TotalGPA = 该学生所有课程 Point 的平均值
                update_gpa_query = """
                    UPDATE Student 
                    SET TotalGPA = (SELECT AVG(Point) FROM Grade WHERE StudentID = ?)
                    WHERE StudentID = ?
                """
                gpa_params = [(sid, sid) for sid in affected_students]
                db_execute_many(update_gpa_query, gpa_params)

                QMessageBox.information(self, "成功", "成绩已保存，且学生绩点已刷新。")
                
                # 3. 刷新表格显示
                self.load_grade_data()
                
            except Exception as e:
                QMessageBox.critical(self, "数据库错误", f"保存失败：\n{e}")

    # --- 选课与导航部分 (已修改) ---
    def create_course_selection_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)

        # 选课操作区域
        selection_layout = QHBoxLayout()
        label = QLabel("选择课程：")
        self.course_combo = QComboBox()
        self.course_combo.setMinimumWidth(300)
        try:
            rows = db_query_all("SELECT CourseID, CourseName FROM Course")
            for row in rows:
                self.course_combo.addItem(f"{row[1]} ({row[0]})", row[0])
        except Exception as e:
            QMessageBox.critical(self, "数据库错误", f"加载课程失败：\n{e}")
        
        select_btn = styled_button("确认选课", style="save")
        select_btn.clicked.connect(self.select_course)

        selection_layout.addWidget(label)
        selection_layout.addWidget(self.course_combo)
        selection_layout.addWidget(select_btn)
        selection_layout.addStretch()
        
        layout.addLayout(selection_layout)

        # 分隔线
        line = QLabel()
        line.setStyleSheet("border-top: 2px solid #ccc; margin: 15px 0;")
        line.setFixedHeight(2)
        layout.addWidget(line)

        # 已选课程列表
        layout.addWidget(QLabel("已选课程列表 (点击 '导航' 查看路线)："))
        self.enrolled_table = QTableWidget()
        headers = ["课程名称", "上课时间", "教室", "教师", "操作"]
        self.enrolled_table.setColumnCount(len(headers))
        self.enrolled_table.setHorizontalHeaderLabels(headers)
        self.enrolled_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.enrolled_table)
        
        self.refresh_enrolled_courses()
        self.tabs.addTab(tab, "学生选课")

    def refresh_enrolled_courses(self):
        if not self.student_id: return
        self.enrolled_table.setRowCount(0)
        try:
            query = """
                SELECT c.CourseName, cs.WeekDay, cs.StartTime, cs.EndTime, cr.Building, t.TeacherName
                FROM StudentCourse sc 
                INNER JOIN Course c ON sc.CourseID = c.CourseID
                LEFT JOIN CourseSchedule cs ON c.CourseID = cs.CourseID
                LEFT JOIN ClassRoom cr ON cs.ClassRoomID = cr.ClassRoomID
                LEFT JOIN Teacher t ON cs.TeacherID = t.TeacherID
                WHERE sc.StudentID = ?
            """
            rows = db_query_all(query, (self.student_id,))
            self.enrolled_table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                course_name, day, start, end, building, teacher = row
                time_str = f"{day} {start}-{end}" if day else "时间未定"
                loc_str = f"{building}" if building else "地点未定"
                teacher_str = str(teacher) if teacher else "未知"
                
                self.enrolled_table.setItem(i, 0, QTableWidgetItem(str(course_name)))
                self.enrolled_table.setItem(i, 1, QTableWidgetItem(time_str))
                self.enrolled_table.setItem(i, 2, QTableWidgetItem(loc_str))
                self.enrolled_table.setItem(i, 3, QTableWidgetItem(teacher_str))
                
                nav_btn = QPushButton("📍 导航")
                nav_btn.setStyleSheet("QPushButton { background-color: #2ecc71; color: white; border-radius: 4px; padding: 5px; }")
                # 传递 building 字段给导航函数
                nav_btn.clicked.connect(partial(self.navigate_to_classroom, building))
                self.enrolled_table.setCellWidget(i, 4, nav_btn)
        except Exception as e:
            print(f"刷新课程列表失败: {e}")

    def select_course(self):
        course_id = self.course_combo.currentData()
        if not course_id or not self.student_id:
            QMessageBox.warning(self, "错误", "无效的课程或学生ID。")
            return
        try:
            max_students = db_query_one("SELECT MaxStudents FROM Course WHERE CourseID = ?", (course_id,))[0]
            current_count = db_query_one("SELECT COUNT(*) FROM StudentCourse WHERE CourseID = ?", (course_id,))[0]
            if current_count >= max_students:
                QMessageBox.warning(self, "满员", "该课程已满！")
                return
        except Exception as e:
            QMessageBox.critical(self, "数据库错误", f"检查选课上限失败：\n{e}")
            return

        if self.has_schedule_conflict(course_id):
            QMessageBox.warning(self, "冲突", "该课程与已选课程时间冲突！")
            return

        try:
            db_execute("INSERT INTO StudentCourse (StudentID, CourseID) VALUES (?, ?)", (self.student_id, course_id))
            QMessageBox.information(self, "成功", "选课成功！")
            self.refresh_enrolled_courses()
        except Exception as e:
            if "unique" in str(e).lower():
                QMessageBox.warning(self, "重复", "您已选此课程！")
            else:
                QMessageBox.critical(self, "数据库错误", f"选课失败：\n{e}")

    def has_schedule_conflict(self, new_course_id):
        try:
            new_schedules = db_query_all("SELECT WeekDay, StartTime, EndTime FROM CourseSchedule WHERE CourseID = ?", (new_course_id,))
            existing_schedules = db_query_all(
                """
                SELECT cs.WeekDay, cs.StartTime, cs.EndTime
                FROM StudentCourse sc INNER JOIN CourseSchedule cs ON sc.CourseID = cs.CourseID
                WHERE sc.StudentID = ?
                """, (self.student_id,)
            )
            for new_day, new_start, new_end in new_schedules:
                for ex_day, ex_start, ex_end in existing_schedules:
                    if new_day == ex_day and ((new_start < ex_end and new_end > ex_start) or (ex_start < new_end and ex_end > new_start)):
                        return True
            return False
        except Exception:
            return True

    def create_schedule_export_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        export_btn = styled_button("导出课程表到CSV")
        export_btn.clicked.connect(self.export_schedule)
        layout.addWidget(export_btn)
        self.tabs.addTab(tab, "课程表导出")

    def export_schedule(self):
        if not self.student_id:
            QMessageBox.warning(self, "错误", "无效的学生ID。")
            return
        try:
            rows = db_query_all(
                """
                SELECT c.CourseName, cs.WeekDay, cs.StartTime, cs.EndTime, cr.Building, t.TeacherName
                FROM StudentCourse sc INNER JOIN Course c ON sc.CourseID = c.CourseID
                                      INNER JOIN CourseSchedule cs ON c.CourseID = cs.CourseID
                                      INNER JOIN ClassRoom cr ON cs.ClassRoomID = cr.ClassRoomID
                                      INNER JOIN Teacher t ON cs.TeacherID = t.TeacherID
                WHERE sc.StudentID = ?
                """, (self.student_id,)
            )
            if not rows:
                QMessageBox.information(self, "提示", "没有课程数据可导出。")
                return
            with open('schedule.csv', 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["课程名", "星期", "开始时间", "结束时间", "教学楼", "教师"])
                writer.writerows(rows)
            QMessageBox.information(self, "成功", "课程表已导出到 schedule.csv")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败：\n{e}")

    def create_map_tab(self):
        self.map_widget = MapWidget()
        self.tabs.addTab(self.map_widget, "校园地图")

    def navigate_to_classroom(self, target_building):
        """
        导航逻辑：
        1. 根据性别确定起点 (男: A2, 女: A6)
        2. 根据教室建筑确定终点 (实验楼->G5, 教一楼->E3, 教二楼->F4)
        """
        if hasattr(self, 'map_widget'):
            self.tabs.setCurrentWidget(self.map_widget)
        
        # 1. 确定起点
        gender_str = str(self.student_gender).strip()
        is_male = "男" in gender_str or "Male" in gender_str or "male" in gender_str
        
        if is_male:
            start_node = "A2"
            start_desc = "男生宿舍(A2)"
        else:
            start_node = "A6"
            start_desc = "女生宿舍(A6)"

        # 2. 确定终点
        building_map = {
            "实验楼": "G5",
            "教一楼": "E3",
            "教二楼": "F4"
        }
        
        end_node = building_map.get(target_building)
        
        if not end_node:
            QMessageBox.warning(self, "导航未知", f"无法识别建筑 '{target_building}' 的地图位置。\n仅支持：实验楼、教一楼、教二楼。")
            return

        # 3. 执行寻路
        if start_node in self.map_widget.nodes and end_node in self.map_widget.nodes:
            self.map_widget.start_node = start_node
            self.map_widget.end_node = end_node
            path, dist = self.map_widget.dijkstra(start_node, end_node)
            self.map_widget.highlight_path(path, dist)
            self.map_widget.update_tip(f"导航：{start_desc} -> {target_building}({end_node})\n距离：{dist:.2f}米")
        else:
            QMessageBox.warning(self, "数据缺失", f"地图节点缺失：{start_node} 或 {end_node}。请检查Nodes表。")