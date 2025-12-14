# repository/call_log_crud.py
from config.database import execute_sql
import os
import json
from typing import List, Optional
from repository.entity.sql_entity import t_call_log


def load_sql(name: str):
    """加载SQL语句"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sql_file = os.path.join(current_dir, "sql", "call_log.sql")

    if not os.path.exists(sql_file):
        raise FileNotFoundError(f"SQL 文件未找到: {sql_file}")

    with open(sql_file, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = content.split("-- name: ")
    for block in blocks:
        if block.strip().startswith(name):
            return "\n".join(block.split("\n")[1:]).strip()
    raise ValueError(f"SQL '{name}' 未找到")


def create_call_log_table():
    """创建调用日志表"""
    sql = load_sql("create_call_log_table")
    execute_sql(sql)


def insert_call_log(call_log: t_call_log):
    """插入调用日志"""
    sql = load_sql("insert_call_log")
    
    # 处理JSON数据的序列化
    input_data = json.dumps(call_log.input_data, ensure_ascii=False) if call_log.input_data else None
    output_data = json.dumps(call_log.output_data, ensure_ascii=False) if call_log.output_data else None
    
    execute_sql(sql, {
        "request_id": call_log.request_id,
        "stage": call_log.stage,
        "step_order": call_log.step_order,
        "operation": call_log.operation,
        "input_data": input_data,
        "output_data": output_data,
        "status": call_log.status,
        "error_message": call_log.error_message,
        "execution_time": call_log.execution_time,
        "timestamp": call_log.timestamp,
        "endpoint_path": call_log.endpoint_path,
        "endpoint_method": call_log.endpoint_method
    })


def get_call_logs_by_request_id(request_id: str) -> List[t_call_log]:
    """根据请求ID获取调用日志"""
    sql = load_sql("get_call_logs_by_request_id")
    rows = execute_sql(sql, {"request_id": request_id}, fetch="all")
    
    logs = []
    for row in rows:
        # 处理JSON数据的反序列化
        input_data = json.loads(row["input_data"]) if row["input_data"] else None
        output_data = json.loads(row["output_data"]) if row["output_data"] else None
        
        log = t_call_log(
            id=row["id"],
            request_id=row["request_id"],
            stage=row["stage"],
            step_order=row["step_order"],
            operation=row["operation"],
            input_data=input_data,
            output_data=output_data,
            status=row["status"],
            error_message=row["error_message"],
            execution_time=row["execution_time"],
            timestamp=row["timestamp"],
            endpoint_path=row["endpoint_path"],
            endpoint_method=row["endpoint_method"]
        )
        logs.append(log)
    
    return logs


def get_all_call_logs(limit: int = 100, offset: int = 0) -> List[t_call_log]:
    """获取所有调用日志"""
    sql = load_sql("get_all_call_logs")
    rows = execute_sql(sql, {"limit": limit, "offset": offset}, fetch="all")
    
    logs = []
    for row in rows:
        # 处理JSON数据的反序列化
        input_data = json.loads(row["input_data"]) if row["input_data"] else None
        output_data = json.loads(row["output_data"]) if row["output_data"] else None
        
        log = t_call_log(
            id=row["id"],
            request_id=row["request_id"],
            stage=row["stage"],
            step_order=row["step_order"],
            operation=row["operation"],
            input_data=input_data,
            output_data=output_data,
            status=row["status"],
            error_message=row["error_message"],
            execution_time=row["execution_time"],
            timestamp=row["timestamp"],
            endpoint_path=row["endpoint_path"],
            endpoint_method=row["endpoint_method"]
        )
        logs.append(log)
    
    return logs


def delete_call_logs_by_request_id(request_id: str):
    """根据请求ID删除调用日志"""
    sql = load_sql("delete_call_logs_by_request_id")
    execute_sql(sql, {"request_id": request_id})