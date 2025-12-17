from pydantic import BaseModel
from typing import Optional
class BaseAIRequest(BaseModel):
    """
    AI请求基础模型
    包含所有AI模型通用的参数
    """
    prompt: str
    model: str = "wanx2.1-t2v-plus"  # 使用正确的默认文生视频模型名称
    negative_prompt: Optional[str] = None  # 反向提示词
    prompt_extend: Optional[bool] = True  # 是否启用提示词扩写
    seed: Optional[int] = None  # 随机种子，用于控制生成结果的一致性
    
class BaseAIResponse(BaseModel):
    """
    AI响应基础模型
    包含所有AI模型通用的响应字段
    """
    task_id: Optional[str] = None
    request_id: Optional[str] = None
    status: Optional[str] = None
    message: Optional[str] = None
    error_code: Optional[str] = None