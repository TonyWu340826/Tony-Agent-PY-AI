# model/dashscope_model.py
from http import HTTPStatus
from dashscope import Application, MultiModalConversation, VideoSynthesis
from typing import Optional
import os
import base64
from dotenv import load_dotenv
from core.logger import logger

load_dotenv()

class DashScopeModel:
    """
    DashScope AI模型接口封装类
    
    该类封装了阿里云DashScope平台的各种AI模型调用接口，
    包括文本生成、文生图、图生文、文生视频等功能。
    """

    def __init__(self, api_key: str = None, app_id: str = None, system_prompt: str = None):
        """
        初始化DashScopeModel实例
        
        Args:
            api_key (str, optional): DashScope API密钥，如果未提供则从环境变量DASHSCOPE_API_KEY获取
            app_id (str, optional): 应用ID，如果未提供则从环境变量DASHSCOPE_APP_ID获取
            system_prompt (str, optional): 系统提示词，用于设定AI的行为模式
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.app_id = app_id or os.getenv("DASHSCOPE_APP_ID")

        # 设置实例级别的系统提示词
        self.system_prompt = system_prompt or """
        你是一个简洁高效的AI，回答问题直击要点,可以多做个总结性的内容。
        """
        logger.info("DashScopeModel 初始化完成...")

    def call(self, prompt: str) -> Optional[str]:
        """
        调用DashScope应用模型生成文本
        
        该方法使用Application.call接口调用已部署的DashScope应用，
        结合系统提示词和用户输入生成响应文本。
        
        Args:
            prompt (str): 用户输入的提示词
            
        Returns:
            Optional[str]: 成功时返回生成的文本，失败时返回错误信息
        """
        logger.info(f"开始调用智能体 request>>>prompt={prompt}")

        # 使用实例的 system_prompt
        final_prompt = f"{self.system_prompt.strip()}\n\n用户输入：{prompt.strip()}"

        logger.info(f"开始调用智能体 request>>>final_prompt={final_prompt}")

        try:
            resp = Application.call(
                api_key=self.api_key,
                app_id=self.app_id,
                prompt=final_prompt
            )
            # ... (处理响应)
            if resp.status_code == HTTPStatus.OK:
                logger.info(f"智能体结果 request>>>response={resp.output.text}")
                return resp.output.text
            else:
                return f"错误：{resp.message}"
        except Exception as e:
            return f"调用失败：{str(e)}"

    def text_to_image(
            self,
            prompt: str,
            negative_prompt: str = "",
            size: str = "1024*1024",
            model: str = "qwen-image-plus",  # 或 "wanx-v2"
            watermark: bool = False,
            prompt_extend: bool = True
    ) -> Optional[dict]:
        """
        文生图：根据文本提示词生成图像
        
        使用MultiModalConversation.call接口调用文生图模型，
        根据正向和反向提示词生成相应的图像。
        
        Args:
            prompt (str): 正向提示词（必须），描述希望生成的画面内容
            negative_prompt (str): 反向提示词（可选），描述不希望出现的内容
            size (str): 图像尺寸，如 "1024*1024"、"1328*1328" 等
            model (str): 模型名称，默认使用 qwen-image-plus（即 wanx-v2）
            watermark (bool): 是否添加阿里云水印
            prompt_extend (bool): 是否启用自动扩写（通常建议开启）
            
        Returns:
            Optional[dict]: 成功时返回 DashScope 响应对象（可转 dict），失败返回 None
        """
        if not prompt.strip():
            logger.warning("正向提示词为空，无法生成图像")
            return None

        logger.info(f"文生图请求 - 正向: {prompt} | 反向: {negative_prompt}")

        messages = [
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]

        try:
            response = MultiModalConversation.call(
                api_key=self.api_key,
                model=model,
                messages=messages,
                result_format='message',
                stream=False,
                watermark=watermark,
                prompt_extend=prompt_extend,
                negative_prompt=negative_prompt,  # 👈 关键：传入反向提示词
                size=size
            )

            if response.status_code == HTTPStatus.OK:
                logger.info("文生图成功")
                return response
            else:
                logger.error(
                    f"文生图失败 - code: {response.code}, message: {response.message}"
                )
                return None

        except Exception as e:
            logger.exception(f"调用文生图接口异常: {e}")
            return None

    def image_to_text(self, image_content: str, prompt: str, model: str = "qwen-vl-plus") -> Optional[str]:
        """
        图生文：根据图片和提示词生成文本描述
        
        使用MultiModalConversation.call接口调用图生文模型，
        根据输入图片和提示词生成相应的文本描述。
        
        Args:
            image_content (str): 图片的Base64编码或URL
            prompt (str): 提示词
            model (str): 模型名称，默认使用qwen-vl-plus
            
        Returns:
            Optional[str]: 成功时返回文本描述，失败返回None
        """
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": image_content},
                        {"text": prompt}
                    ]
                }
            ]
            response = MultiModalConversation.call(
                api_key=self.api_key,
                model=model,
                messages=messages
            )
            if response.status_code == HTTPStatus.OK:
                return response.output.choices[0].message.content[0]["text"]
            else:
                logger.error(f"图生文失败 - code: {response.code}, message: {response.message}")
                return None
                
        except Exception as e:
            logger.exception(f"调用图生文接口异常: {e}")
            return None

    def text_to_video(
            self,
            prompt: str,
            negative_prompt: str = "",
            size: str = "1280*720",
            duration: int = 5,
            model: str = "wanx2.1-t2v-plus",  # 使用正确的文生视频模型名称
            audio: bool = True,
            audio_url: str = None,
            prompt_extend: bool = True,
            watermark: bool = False,
            seed: int = None
    ) -> Optional[dict]:
        """
        文生视频：根据文本提示词生成视频（同步调用，直接返回结果）
        
        使用VideoSynthesis.call接口调用文生视频模型，
        根据文本提示词生成相应的视频内容，支持音频、水印等高级功能。
        
        支持的文生视频模型列表：
        1. wanx2.1-t2v-plus（推荐）
           - 类型：专业版文生视频模型
           - 特点：质量高，稳定性好
           - 分辨率：支持多种分辨率
           - 时长：通常为5秒
           
        2. wanx2.1-t2v-turbo
           - 类型：极速版文生视频模型
           - 特点：生成速度快
           - 分辨率：支持多种分辨率
           - 时长：通常为5秒
           
        3. wanx-txt2video-pro
           - 类型：文生视频专业版
           - 特点：综合性能优秀
           - 分辨率：支持多种分辨率
           - 时长：根据具体配置而定
           
        注意：不同模型支持的参数可能略有差异，请根据具体模型调整参数。
        
        Args:
            prompt (str): 正向提示词，描述希望生成的视频内容
            negative_prompt (str): 反向提示词，描述不希望出现的内容
            size (str): 视频分辨率，如 "1280*720"、"832*480" 等
            duration (int): 视频时长（秒），可选值通常为5或10
            model (str): 模型名称，默认使用 wanx2.1-t2v-plus
            audio (bool): 是否启用音频（仅适用于支持音频的模型版本）
            audio_url (str): 自定义音频文件URL（可选）
            prompt_extend (bool): 是否启用自动扩写提示词
            watermark (bool): 是否添加阿里云水印
            seed (int): 随机种子，用于控制生成结果的一致性
            
        Returns:
            Optional[dict]: 成功时返回包含视频URL等完整信息的字典，失败返回None
        """
        if not prompt.strip():
            logger.warning("提示词为空，无法生成视频")
            return None

        logger.info(f"文生视频请求 - 提示词: {prompt}")
        
        try:
            # 准备参数
            params = {
                "api_key": self.api_key,
                "model": model,
                "prompt": prompt,
                "size": size,
                "duration": duration,
                "negative_prompt": negative_prompt,
                "prompt_extend": prompt_extend,
                "watermark": watermark
            }
            
            # 添加可选参数
            if audio is not None:
                params["audio"] = audio
            if audio_url:
                params["audio_url"] = audio_url
            if seed is not None:
                params["seed"] = seed
                
            # 调用文生视频API（同步调用）
            response = VideoSynthesis.call(**params)
            
            if response.status_code == HTTPStatus.OK:
                logger.info("文生视频生成成功")
                # 直接返回完整的响应信息
                return {
                    "task_id": response.output.task_id,
                    "task_status": response.output.task_status,
                    "video_url": response.output.video_url,
                    "submit_time": response.output.submit_time,
                    "scheduled_time": response.output.scheduled_time,
                    "end_time": response.output.end_time,
                    "orig_prompt": response.output.orig_prompt,
                    "actual_prompt": response.output.actual_prompt,
                    "usage": {
                        "video_count": response.usage.video_count,
                        "video_duration": response.usage.video_duration,
                        "video_ratio": response.usage.video_ratio
                    },
                    "request_id": response.request_id
                }
            else:
                logger.error(
                    f"文生视频生成失败 - code: {response.code}, message: {response.message}"
                )
                return None
                
        except Exception as e:
            logger.exception(f"调用文生视频接口异常: {e}")
            return None
            
    def get_video_generation_result(self, task_id: str) -> Optional[dict]:
        """
        获取视频生成任务的结果（异步查询）
        
        使用VideoSynthesis.fetch接口查询指定任务ID的视频生成结果，
        适用于异步调用场景或需要重新查询已完成任务的情况。
        
        Args:
            task_id (str): 视频生成任务的ID
            
        Returns:
            Optional[dict]: 成功时返回包含视频URL等信息的字典，失败返回None
        """
        if not task_id:
            logger.warning("任务ID为空")
            return None
            
        try:
            logger.info(f"查询视频生成任务结果 - task_id: {task_id}")
            
            # 调用API查询任务结果
            response = VideoSynthesis.fetch(
                api_key=self.api_key,
                task_id=task_id
            )
            
            if response.status_code == HTTPStatus.OK:
                logger.info("视频生成任务查询成功")
                return {
                    "task_id": response.output.task_id,
                    "status": response.output.status,
                    "video_url": getattr(response.output, 'video_url', None),
                    "request_id": response.request_id,
                    "code": response.code
                }
            else:
                logger.error(
                    f"视频生成任务查询失败 - code: {response.code}, message: {response.message}"
                )
                return None
                
        except Exception as e:
            logger.exception(f"查询视频生成任务结果异常: {e}")
            return None