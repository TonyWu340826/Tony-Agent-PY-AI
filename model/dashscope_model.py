# model/dashscope_model.py
from http import HTTPStatus
from dashscope import Application, MultiModalConversation
from typing import Optional
import os
import base64
from dotenv import load_dotenv
from core.logger import logger

load_dotenv()

class DashScopeModel:

    def __init__(self, api_key: str = None, app_id: str = None, system_prompt: str = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.app_id = app_id or os.getenv("DASHSCOPE_APP_ID")

        # 设置实例级别的系统提示词
        self.system_prompt = system_prompt or """
        你是一个简洁高效的AI，回答问题直击要点,可以多做个总结性的内容。
        """
        logger.info("DashScopeModel 初始化完成...")

    def call(self, prompt: str) -> Optional[str]:
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
        文生图：用户传入正向提示词和反向提示词

        Args:
            prompt (str): 正向提示词（必须），描述希望生成的画面内容
            negative_prompt (str): 反向提示词（可选），描述不希望出现的内容
            size (str): 图像尺寸，如 "1024*1024"、"1328*1328" 等
            model (str): 模型名称，默认使用 qwen-image-plus（即 wanx-v2）
            watermark (bool): 是否添加阿里云水印
            prompt_extend (bool): 是否启用自动扩写（通常建议开启）

        Returns:
            成功时返回 DashScope 响应对象（可转 dict），失败返回 None
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
        Args:
            image_content (str): 图片的Base64编码或URL
            prompt (str): 提示词
            model (str): 模型名称
        Returns:
            成功时返回文本描述，失败返回None
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