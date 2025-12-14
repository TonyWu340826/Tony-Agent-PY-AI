from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from repository.call_log_crud import get_call_logs_by_request_id, get_all_call_logs, delete_call_logs_by_request_id
from repository.entity.sql_entity import t_call_log

router = APIRouter(prefix="/call-log", tags=["调用日志"])

class CallLogResponse(BaseModel):
    logs: List[t_call_log]
    count: int

@router.get("/{request_id}", response_model=CallLogResponse)
async def get_call_logs(request_id: str):
    """根据请求ID获取调用日志"""
    try:
        logs = get_call_logs_by_request_id(request_id)
        return CallLogResponse(logs=logs, count=len(logs))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取调用日志失败: {str(e)}")

@router.get("/", response_model=CallLogResponse)
async def get_all_logs(limit: int = 100, offset: int = 0):
    """获取所有调用日志"""
    try:
        logs = get_all_call_logs(limit, offset)
        return CallLogResponse(logs=logs, count=len(logs))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取调用日志失败: {str(e)}")

@router.delete("/{request_id}")
async def delete_logs(request_id: str):
    """根据请求ID删除调用日志"""
    try:
        delete_call_logs_by_request_id(request_id)
        return {"message": "调用日志删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除调用日志失败: {str(e)}")