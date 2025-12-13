# repository/crud.py
from config.database import execute_sql
import os

def load_sql(name: str):
    # 动态获取 sql/user.sql 路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sql_file = os.path.join(current_dir, "sql", "user.sql")

    if not os.path.exists(sql_file):
        raise FileNotFoundError(f"SQL 文件未找到: {sql_file}")

    with open(sql_file, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = content.split("-- name: ")
    for block in blocks:
        if block.strip().startswith(name):
            return "\n".join(block.split("\n")[1:]).strip()
    raise ValueError(f"SQL '{name}' 未找到")


# 🟢 创建用户
def create_user(id: int, name: str, address: str, sex: int):
    sql = load_sql("create_user")
    execute_sql(sql, {
        "id": id,
        "name": name,
        "address": address,
        "sex": sex
    })

# 🔵 查询用户
def get_user_by_id(user_id: int):
    sql = load_sql("get_user_by_id")
    return execute_sql(sql, {"user_id": user_id}, fetch="one")

def get_all_users(skip: int = 0, limit: int = 10):
    sql = load_sql("get_all_users")
    return execute_sql(sql, {"offset": skip, "limit": limit}, fetch="all")

# 🟡 更新用户
def update_user(id: int, name: str = None, address: str = None, sex: int = None):
    sql = load_sql("update_user")
    execute_sql(sql, {
        "id": id,
        "name": name,
        "address": address,
        "sex": sex
    })

# 🔴 删除用户
def delete_user(id: int):
    sql = load_sql("delete_user")
    execute_sql(sql, {"id": id})










# repository/crud.py
from config.database import execute_sql
from typing import Optional, Dict, Any

def exec_any_sql(sql: str, params: Optional[Dict[str, Any]] = None, fetch: str = "auto"):
    """
    通用 SQL 执行方法，用于执行任意 SQL
    fetch:
      - "none": 不返回结果（如INSERT/UPDATE/DELETE）
      - "one": 返回单行
      - "all": 返回多行
      - "auto": 自动根据语句判断（SELECT -> all）
    """
    sql_lower = sql.strip().lower()
    if fetch == "auto":
        if sql_lower.startswith("select"):
            fetch = "all"
        else:
            fetch = "none"
    return execute_sql(sql, params or {}, fetch=fetch)













