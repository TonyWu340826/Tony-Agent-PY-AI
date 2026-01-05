# model/embedding_model.py
from http import HTTPStatus
import dashscope
from typing import List, Union, Optional
import os
from dotenv import load_dotenv
from core.logger import logger

# 加载环境变量
load_dotenv()

class TextEmbeddingModel:
    """
    DashScope文本嵌入模型接口封装类
    
    该类封装了阿里云DashScope平台的文本嵌入模型调用接口，
    用于将文本转换为向量表示，支持单个文本或批量文本嵌入。
    """
    
    def __init__(self, api_key: str = None, model: str = "text-embedding-v4"):
        """
        初始化文本嵌入模型实例
        
        Args:
            api_key (str, optional): DashScope API密钥，如果未提供则从环境变量DASHSCOPE_API_KEY获取
            model (str): 使用的嵌入模型，默认为text-embedding-v4
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY")
        self.model = model
        
        if not self.api_key:
            raise ValueError("API密钥未提供。请设置环境变量DASHSCOPE_API_KEY或在代码中传入api_key参数")
        
        # 设置dashscope的API密钥
        dashscope.api_key = self.api_key
        logger.info(f"TextEmbeddingModel 初始化完成，使用模型: {model}")
        
    def embed_text(self, input_text: Union[str, List[str]], model: str = None, dimensions: int = None) -> Optional[dict]:
        """
        将文本转换为嵌入向量
        
        Args:
            input_text: 输入的文本，可以是单个字符串或字符串列表
            model: 使用的嵌入模型，如果提供则覆盖初始化时设置的模型
            dimensions: 指定向量维度，不同模型支持的维度可能不同
            
        Returns:
            Optional[dict]: 成功时返回包含嵌入向量的响应字典，失败时返回错误信息
        """
        logger.info(f"开始文本嵌入 request>>>input_text={input_text}, model={model or self.model}, dimensions={dimensions}")
        
        # 构建参数
        params = {
            "model": model or self.model,
            "input": input_text,
        }
        
        # 如果指定了维度，则添加到参数中
        if dimensions is not None:
            params["dimensions"] = dimensions
        
        try:
            resp = dashscope.TextEmbedding.call(**params)
            
            if resp.status_code == HTTPStatus.OK:
                logger.info("文本嵌入成功")
                return {
                    "success": True,
                    "data": resp,
                    "embedding": resp.output['embeddings'][0]['embedding'] if resp.output.get('embeddings') and len(resp.output['embeddings']) > 0 else None,
                    "usage": resp.usage,
                    "model": resp.output.get('model', model or self.model),
                    "total_tokens": resp.usage.get('total_tokens', 0) if resp.usage else 0
                }
            else:
                logger.error(f"文本嵌入失败 - code: {resp.code}, message: {resp.message}")
                return {
                    "success": False,
                    "error": f"API调用失败，错误码: {resp.code}, 消息: {resp.message}",
                    "data": resp
                }
                
        except Exception as e:
            logger.exception(f"调用文本嵌入接口异常: {e}")
            return {
                "success": False,
                "error": f"调用失败：{str(e)}",
                "data": None
            }
    
    def get_embedding_vector(self, input_text: Union[str, List[str]], model: str = None, dimensions: int = None) -> Union[List[float], List[List[float]], None]:
        """
        获取文本的嵌入向量
        
        Args:
            input_text: 输入的文本，可以是单个字符串或字符串列表
            model: 使用的嵌入模型，如果提供则覆盖初始化时设置的模型
            dimensions: 指定向量维度，不同模型支持的维度可能不同
            
        Returns:
            Union[List[float], List[List[float]], None]: 嵌入向量或向量列表，如果失败则返回None
        """
        result = self.embed_text(input_text, model, dimensions)
        
        if result and result["success"]:
            return result["embedding"]
        else:
            error_msg = result["error"] if result else "未知错误"
            logger.error(f"获取嵌入向量失败: {error_msg}")
            return None


# 使用示例
if __name__ == "__main__":
    try:
        # 创建嵌入实例 - 从环境变量获取API密钥
        embedder = TextEmbeddingModel()
        
        # 单个文本嵌入
        input_text = "衣服的质量杠杠的"
        result = embedder.embed_text(input_text)
        print("单个文本嵌入结果:")
        print(result)
        
        # 获取向量
        vector = embedder.get_embedding_vector(input_text)
        print(f"\n嵌入向量长度: {len(vector) if vector else 0}")
        print(f"向量前5个值: {vector[:5] if vector else None}")
        
        # 使用不同模型进行嵌入
        print("\n使用不同模型进行嵌入:")
        result_v1 = embedder.embed_text(input_text, model="text-embedding-v1")
        print(f"text-embedding-v1 结果: {result_v1['success'] if result_v1 else '失败'}")
        
        # 指定维度进行嵌入（如果模型支持）
        print("\n指定维度进行嵌入:")
        result_dim = embedder.embed_text(input_text, model="text-embedding-v4", dimensions=512)
        print(f"指定维度嵌入结果: {result_dim['success'] if result_dim else '失败'}")
        
        # 批量文本嵌入
        input_texts = ["衣服的质量杠杠的", "这个产品非常棒", "推荐购买"]
        result_batch = embedder.embed_text(input_texts)
        print(f"\n批量嵌入结果: {result_batch['success'] if result_batch else '失败'}")
        
    except ValueError as e:
        print(f"错误: {e}")
        print("\n请设置API密钥后重试。设置方法：")
        print("1. 在.env文件中添加: DASHSCOPE_API_KEY=your_api_key")
        print("2. 或设置环境变量: DASHSCOPE_API_KEY=your_api_key")
        print("3. 或在代码中直接传入API密钥: TextEmbeddingModel(api_key='your_api_key')")