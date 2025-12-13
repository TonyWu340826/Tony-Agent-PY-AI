from typing import Optional, Any, Dict
from pydantic import BaseModel  # 注意：不是 openai.BaseModel！

# ==============================
# 响应 Code 常量定义
# ==============================
class ResponseCode:
    SUCCESS = 0
    BAD_REQUEST = 10000      # 参数错误、业务逻辑错误等
    INTERNAL_ERROR = 50000   # 网络异常、LLM 调用失败、服务器内部错误等

# ==============================
# 请求模型
# ==============================
class AskRequest(BaseModel):
    user_message: str
    system_prompt: Optional[str] = None

# ==============================
# 统一响应模型
# ==============================
class StandardResponse(BaseModel):
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None  # 更通用的 data 类型

    @classmethod
    def success(cls, data: Optional[Dict[str, Any]] = None, message: str = "success") -> "StandardResponse":
        return cls(code=ResponseCode.SUCCESS, message=message, data=data)

    @classmethod
    def fail(
        cls,
        message: str,
        code: int = ResponseCode.INTERNAL_ERROR
    ) -> "StandardResponse":
        return cls(code=code, message=message, data=None)