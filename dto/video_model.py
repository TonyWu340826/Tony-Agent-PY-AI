from pydantic import BaseModel
from typing import Optional
from dto.base_model import BaseAIRequest, BaseAIResponse

class VideoGenerationRequest(BaseAIRequest):
    """
    视频生成请求模型
    继承基础AI请求模型，添加视频生成特有的参数
    """
    size: str = "1280*720"  # 视频分辨率
    duration: int = 5  # 视频时长（秒）
    audio: Optional[bool] = True  # 是否启用音频
    audio_url: Optional[str] = None  # 自定义音频文件URL
    watermark: Optional[bool] = False  # 是否添加水印
    
class VideoGenerationResponse(BaseAIResponse):
    """
    视频生成响应模型
    继承基础AI响应模型，添加视频生成特有的响应字段
    """
    video_url: Optional[str] = None
    submit_time: Optional[str] = None
    scheduled_time: Optional[str] = None
    end_time: Optional[str] = None
    orig_prompt: Optional[str] = None
    actual_prompt: Optional[str] = None
    usage: Optional[dict] = None  # 包含video_count, video_duration, video_ratio等信息