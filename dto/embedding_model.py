from pydantic import BaseModel
from typing import List, Optional, Union


class EmbeddingRequest(BaseModel):
    """
    文本嵌入请求DTO
    """
    texts: Union[str, List[str]]  # 支持单个文本或文本列表
    model: Optional[str] = "text-embedding-v4"  # 模型名称
    dimensions: Optional[int] = None  # 向量维度


class EmbeddingItem(BaseModel):
    """
    单个文本嵌入结果
    """
    text: str  # 原始文本
    embedding: List[float]  # 嵌入向量


class EmbeddingResponse(BaseModel):
    """
    文本嵌入响应DTO
    """
    success: bool  # 整体是否成功
    embeddings: List[EmbeddingItem]  # 嵌入结果列表
    model: Optional[str] = None  # 使用的模型
    total_tokens: Optional[int] = 0  # 总token数
    error: Optional[str] = None  # 整体错误信息（如果失败）


class DocumentUploadRequest(BaseModel):
    """
    文档上传请求DTO
    """
    doc_type: str  # 文档类型 (doc, pdf, txt)
    doc_subject: str  # 文档主题
    org_code: str  # 组织编码
    chunk_size: Optional[int] = 512  # 切分大小，默认512
    overlap: Optional[int] = 50  # 切分重叠大小，默认50


class DocumentSearchRequest(BaseModel):
    """
    文档搜索请求DTO
    """
    query: str  # 查询文本
    org_code: str  # 组织编码
    top_k: Optional[int] = 10  # 返回结果数量，默认10


class DocumentSearchResult(BaseModel):
    """
    单个文档搜索结果
    """
    id: int  # 文档ID
    doc_type: str  # 文档类型
    doc_subject: str  # 文档主题
    similarity: float  # 相似度分数
    embedding_content: str  # 嵌入的文本内容（从数据库获取）


class DocumentSearchResponse(BaseModel):
    """
    文档搜索响应DTO
    """
    success: bool  # 是否成功
    results: List[DocumentSearchResult]  # 搜索结果列表
    query: str  # 原始查询
    org_code: str  # 组织编码
    error: Optional[str] = None  # 错误信息