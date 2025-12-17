from model import DashScopeModel, get_dashscope_model
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from dto.user_model import ImageUnderstandingBase64Request, ImageUnderstandingUploadRequest
from dto.video_model import VideoGenerationRequest, VideoGenerationResponse

from model import get_dashscope_model
router = APIRouter(prefix="/aliyun_ai", tags=["对接阿里云百炼平台的大模型"])


'''
文生视频
'''
@router.post("/video/videoSynthesis", response_model=VideoGenerationResponse)
async def video_synthesis(request: VideoGenerationRequest, model: DashScopeModel = Depends(get_dashscope_model)):
    """
    文生视频接口
    
    通过文本提示词生成视频内容
    
    Args:
        request (VideoGenerationRequest): 视频生成请求参数
        model (DashScopeModel): DashScope模型实例
        
    Returns:
        VideoGenerationResponse: 视频生成结果
    """
    try:
        # 调用DashScopeModel的text_to_video方法
        result = model.text_to_video(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt or "",
            size=request.size,
            duration=request.duration,
            model=request.model,
            audio=request.audio,
            audio_url=request.audio_url,
            prompt_extend=request.prompt_extend,
            watermark=request.watermark,
            seed=request.seed
        )
        
        # 如果调用成功，返回结果
        if result:
            return VideoGenerationResponse(
                task_id=result.get("task_id"),
                request_id=result.get("request_id"),
                status=result.get("task_status"),
                video_url=result.get("video_url"),
                submit_time=result.get("submit_time"),
                scheduled_time=result.get("scheduled_time"),
                end_time=result.get("end_time"),
                orig_prompt=result.get("orig_prompt"),
                actual_prompt=result.get("actual_prompt"),
                usage=result.get("usage")
            )
        else:
            # 如果调用失败，返回错误信息
            return VideoGenerationResponse(
                status="FAILED",
                message="视频生成失败",
                error_code="VIDEO_GENERATION_FAILED"
            )
            
    except Exception as e:
        # 捕获异常并返回错误信息
        return VideoGenerationResponse(
            status="ERROR",
            message=str(e),
            error_code="INTERNAL_ERROR"
        )