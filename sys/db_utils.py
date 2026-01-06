# File: db_utils.py
# Functionality: 负责数据库连接与查询执行，提供用于操作 SQL Server 数据库的工具函数

import pyodbc

DB_DRIVER = "ODBC Driver 17 for SQL Server"
DB_SERVER = r"(local)"
DB_NAME = "SchoolDB2"
USER_TABLE = "UserInfo"
USERNAME_COLUMN = "Username"
USERID_COLUMN = "UserID"
PASSWORD_COLUMN = "Password"
USERTYPE_COLUMN = "UserType"

def get_db_connection():
    """Establishes and returns a connection to the SQL Server database."""
    conn_str = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)

def db_query_all(query, params=()):
    """Executes a query and fetches all rows."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params) if params else cursor.execute(query)
        rows = cursor.fetchall()
        return rows
    finally:
        conn.close()

def db_query_one(query, params=()):
    """Executes a query and fetches one row."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params) if params else cursor.execute(query)
        row = cursor.fetchone()
        return row
    finally:
        conn.close()

def db_execute(query, params=()):
    """Executes a non-query command (INSERT/UPDATE/DELETE) and commits changes."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params) if params else cursor.execute(query)
        conn.commit()
    finally:
        conn.close()

def db_execute_many(query, params_list):
    """Executes multiple non-query commands in batch."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()
    finally:
        conn.close()