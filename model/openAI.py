# mode/aopenai.py
from core.logger import logger
import os
from openai import AsyncOpenAI

# 从环境变量读取 DeepSeek API Key
API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    raise EnvironmentError("Environment variable 'DEEPSEEK_API_KEY' is not set.")

# 初始化异步客户端，指向 DeepSeek API
client = AsyncOpenAI(
    api_key=API_KEY,
    base_url="https://api.deepseek.com",  # DeepSeek 兼容 OpenAI 协议
)


async def chat_completion(
    messages: list,
    model: str = "deepseek-chat",  # DeepSeek 默认聊天模型
    temperature: float = 0.7,
    max_tokens: int = 1000,
):
    """
    调用 DeepSeek 聊天补全 API（兼容 OpenAI 接口）
    :param messages: 对话消息列表，格式如 [{"role": "user", "content": "你好"}]
    :param model: 模型名称，可选 "deepseek-chat"（非思考模式）或 "deepseek-reasoner"（思考模式）
    :param temperature: 生成随机性（0.0 ~ 2.0）
    :param max_tokens: 最大返回 token 数
    :return: 模型回复的文本内容
    """
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        logger.info(f"DeepSeek API response: {response.choices[0].message.content}")
        return response.choices[0].message.content
    except Exception as e:
        # 可根据需要细化错误处理（如配额、网络、参数错误）
        raise RuntimeError(f"DeepSeek API call failed: {str(e)}")