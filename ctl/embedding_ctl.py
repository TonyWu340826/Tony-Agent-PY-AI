from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
import asyncio
import os
import re
import hashlib
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from dto.embedding_model import EmbeddingRequest, EmbeddingResponse, EmbeddingItem, DocumentSearchRequest, DocumentSearchResponse, DocumentSearchResult
from model import get_embedding_model, TextEmbeddingModel
from core.logger import logger
from Embedding.document_embedding_model import DocumentEmbeddingService
from sqlalchemy.orm import Session
from core.dependencies import get_db


# 创建路由
router = APIRouter()


class JavaTextEmbeddingRequest(BaseModel):
    text: str


class JavaTextEmbeddingResponse(BaseModel):
    success: bool
    embedding: Optional[List[float]] = None
    error: Optional[str] = None


class JavaDocumentChunkEmbeddingItem(BaseModel):
    section: Optional[str] = None
    chunk_index: Optional[int] = None
    content: str
    content_hash: str
    embedding: List[float]


class JavaDocumentChunkEmbeddingResponse(BaseModel):
    success: bool
    source_name: Optional[str] = None
    doc_type: Optional[str] = None
    doc_subject: Optional[str] = None
    org_code: Optional[str] = None
    chunk_size: Optional[int] = None
    overlap: Optional[int] = None
    chunks: List[JavaDocumentChunkEmbeddingItem] = []
    error: Optional[str] = None


@router.post("/generate", response_model=EmbeddingResponse)
async def generate_embedding(
    request: EmbeddingRequest, 
    embedding_model: TextEmbeddingModel = Depends(get_embedding_model)
):
    """
    生成文本嵌入向量
    
    支持单个文本或批量文本的向量生成
    """
    try:
        logger.info(f"收到嵌入请求: texts={request.texts}, model={request.model}, dimensions={request.dimensions}")
        
        # 如果输入是单个文本，转换为列表以便统一处理
        texts = request.texts if isinstance(request.texts, list) else [request.texts]
        
        # 用于存储结果的列表
        results = []
        total_tokens = 0
        overall_success = True
        overall_error = None
        
        # 逐个处理文本
        for text in texts:
            try:
                # 生成单个文本的嵌入向量
                result = embedding_model.embed_text(
                    input_text=text,
                    model=request.model,
                    dimensions=request.dimensions
                )
                
                if result and result["success"]:
                    # 添加到结果中
                    embedding_item = EmbeddingItem(
                        text=text,
                        embedding=result["embedding"]
                    )
                    results.append(embedding_item)
                    # 累计token数
                    if "total_tokens" in result:
                        total_tokens += result["total_tokens"]
                else:
                    # 如果有任何一个失败，整体标记为失败
                    overall_success = False
                    overall_error = result.get("error", "未知错误") if result else "API调用失败"
                    # 即使失败也继续处理其他文本
                    
            except Exception as e:
                logger.error(f"处理文本 '{text}' 时发生错误: {str(e)}")
                overall_success = False
                overall_error = str(e)
                # 即使失败也继续处理其他文本
        
        # 构建响应
        response = EmbeddingResponse(
            success=overall_success,
            embeddings=results,
            model=request.model,
            total_tokens=total_tokens,
            error=overall_error
        )
        
        logger.info(f"嵌入请求处理完成，成功: {overall_success}, 处理文本数: {len(texts)}")
        return response
        
    except Exception as e:
        logger.error(f"生成嵌入向量时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"生成嵌入向量失败: {str(e)}")


@router.post("/java/document/chunk-embed", response_model=JavaDocumentChunkEmbeddingResponse)
async def java_document_chunk_embed(
    file: UploadFile = File(...),
    chunk_size: int = 512,
    overlap: int = 50,
    model: Optional[str] = None,
    dimensions: Optional[int] = None,
    db: Session = Depends(get_db),
    embedding_model: TextEmbeddingModel = Depends(get_embedding_model)
):
    """Java 调用专用：上传文件 -> 文档切分 -> 每个 chunk 生成向量 -> 返回向量。

    说明：
    - 输入为 multipart/form-data 的 file 字段（即文件 bytes），不支持传本地路径。
    - 切分/去重流程对齐 DocumentEmbeddingService.process_and_save_document() 的处理方式。
    - 本接口只返回结果，不写入数据库（避免影响原有 /document/upload 行为）。
    """
    logger.info(f"收到 Java 文档切分请求: file={file.filename}, chunk_size={chunk_size}, overlap={overlap}, model={model}, dimensions={dimensions}")
    try:
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ['.txt', '.pdf', '.doc', '.docx']:
            raise HTTPException(status_code=400, detail="不支持的文件类型，仅支持txt、pdf、doc、docx")

        # Step 1: 保存上传文件到临时位置（与 /document/upload 一致的方式）
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as buffer:
            buffer.write(file.file.read())

        try:
            # Step 2: 创建服务（复用其内部的 DocumentProcessor / embedding_model）
            doc_service = DocumentEmbeddingService(db, embedding_model)

            # Step 3: 读取文档内容（txt/pdf/docx）
            content = doc_service.document_processor.read_document(temp_file_path)

            # Step 4: 分组切分（section/chunk_index）
            grouped_chunks = doc_service.document_processor.split_document_grouped(
                content=content,
                chunk_size=chunk_size,
                overlap=overlap
            )

            # Step 5: 对齐入库逻辑的去重：归一化文本 + SHA256
            def normalize_for_hash(text: str) -> str:
                return re.sub(r"\s+", " ", text or "").strip()

            seen_hashes: set[str] = set()
            items: List[JavaDocumentChunkEmbeddingItem] = []

            # Step 6: 逐 chunk 生成向量，并返回（不写库）
            for item in grouped_chunks:
                chunk = str(item.get("content", "") or "").strip()
                if not chunk:
                    continue

                normalized = normalize_for_hash(chunk)
                content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
                if content_hash in seen_hashes:
                    continue
                seen_hashes.add(content_hash)

                embedding = embedding_model.get_embedding_vector(chunk, model=model, dimensions=dimensions)
                if not embedding:
                    continue

                items.append(
                    JavaDocumentChunkEmbeddingItem(
                        section=str(item.get("section", "") or "") or None,
                        chunk_index=int(item.get("chunk_index", 0) or 0),
                        content=chunk,
                        content_hash=content_hash,
                        embedding=embedding
                    )
                )

            return JavaDocumentChunkEmbeddingResponse(
                success=True,
                source_name=file.filename,
                chunk_size=chunk_size,
                overlap=overlap,
                chunks=items,
                error=None
            )
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Java文档切分向量化失败: {str(e)}")
        return JavaDocumentChunkEmbeddingResponse(success=False, error=str(e))


@router.post("/java/text/embed", response_model=JavaTextEmbeddingResponse)
async def java_text_embed(
    request: JavaTextEmbeddingRequest,
    model: Optional[str] = None,
    dimensions: Optional[int] = None,
    embedding_model: TextEmbeddingModel = Depends(get_embedding_model)
):
    """Java 调用专用：输入文本 -> 生成向量 -> 返回向量。"""
    try:
        text = (request.text or "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="text 不能为空")

        embedding = embedding_model.get_embedding_vector(text, model=model, dimensions=dimensions)
        if not embedding:
            return JavaTextEmbeddingResponse(success=False, error="生成向量失败")

        return JavaTextEmbeddingResponse(success=True, embedding=embedding)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Java文本向量化失败: {str(e)}")
        return JavaTextEmbeddingResponse(success=False, error=str(e))


@router.post("/batch-generate", response_model=EmbeddingResponse)
async def batch_generate_embedding(
    request: EmbeddingRequest, 
    embedding_model: TextEmbeddingModel = Depends(get_embedding_model)
):
    """
    批量生成文本嵌入向量（异步版本）
    
    支持批量处理多个文本的向量生成
    """
    try:
        logger.info(f"收到批量嵌入请求: texts={request.texts}, model={request.model}, dimensions={request.dimensions}")
        
        # 如果输入是单个文本，转换为列表
        texts = request.texts if isinstance(request.texts, list) else [request.texts]
        
        # 并发处理多个文本（注意：根据API限制调整并发数）
        semaphore = asyncio.Semaphore(5)  # 限制并发数为5
        
        async def process_text(text: str):
            async with semaphore:
                try:
                    result = embedding_model.embed_text(
                        input_text=text,
                        model=request.model,
                        dimensions=request.dimensions
                    )
                    
                    if result and result["success"]:
                        return EmbeddingItem(
                            text=text,
                            embedding=result["embedding"]
                        )
                    else:
                        return None  # 对于批量处理，我们只返回成功的项目
                except Exception as e:
                    logger.error(f"异步处理文本 '{text}' 时发生错误: {str(e)}")
                    return None
        
        # 并发处理所有文本
        tasks = [process_text(text) for text in texts]
        results = await asyncio.gather(*tasks)
        
        # 过滤掉None值（失败的项目）
        successful_results = [item for item in results if item is not None]
        
        # 检查是否有成功的项目
        overall_success = len(successful_results) > 0
        
        # 计算总token数
        total_tokens = 0
        for item in successful_results:
            # 重新获取token数，因为并发处理时无法直接获取
            temp_result = embedding_model.embed_text(
                input_text=item.text, 
                model=request.model,
                dimensions=request.dimensions
            )
            if temp_result and "total_tokens" in temp_result:
                total_tokens += temp_result["total_tokens"]
        
        response = EmbeddingResponse(
            success=overall_success,
            embeddings=successful_results,
            model=request.model,
            total_tokens=total_tokens,
            error=None if overall_success else "所有文本处理都失败了"
        )
        
        logger.info(f"批量嵌入请求处理完成，成功: {overall_success}, 成功处理文本数: {len(successful_results)}")
        return response
        
    except Exception as e:
        logger.error(f"批量生成嵌入向量时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量生成嵌入向量失败: {str(e)}")


@router.post("/document/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = "",
    doc_subject: str = "",
    org_code: str = "",
    chunk_size: int = 512,
    overlap: int = 50,
    db: Session = Depends(get_db),
    embedding_model: TextEmbeddingModel = Depends(get_embedding_model)
):
    """
    上传文档并生成向量
    """
    try:
        # 验证文件类型
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ['.txt', '.pdf', '.doc', '.docx']:
            raise HTTPException(status_code=400, detail="不支持的文件类型，仅支持txt、pdf、doc、docx")
        
        # 保存上传的文件到临时位置
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as buffer:
            buffer.write(file.file.read())
        
        try:
            # 创建文档向量服务
            doc_service = DocumentEmbeddingService(db, embedding_model)
            
            # 处理文档并保存向量
            saved_embeddings = doc_service.process_and_save_document(
                temp_file_path, doc_type, doc_subject, org_code, chunk_size, overlap
            )
            
            logger.info(f"成功处理文档，生成 {len(saved_embeddings)} 个向量片段")
            
            return {
                "success": True,
                "message": f"成功处理文档，生成 {len(saved_embeddings)} 个向量片段",
                "count": len(saved_embeddings)
            }
        finally:
            # 删除临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except Exception as e:
        logger.error(f"上传文档时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传文档失败: {str(e)}")


@router.post("/document/search", response_model=DocumentSearchResponse)
async def search_documents(
    request: DocumentSearchRequest,
    db: Session = Depends(get_db),
    embedding_model: TextEmbeddingModel = Depends(get_embedding_model)
):
    """
    搜索相似文档
    """
    try:
        # 创建文档向量服务
        doc_service = DocumentEmbeddingService(db, embedding_model)
        
        # 搜索相似文档
        # 先扩大候选集，再做“按 section 限流”，避免单一章节霸榜导致结果重复
        candidate_k = max(int(request.top_k or 10) * 5, int(request.top_k or 10))
        similarities = doc_service.search_similar_documents(
            request.query, request.org_code, candidate_k
        )
        
        # 按 section 限流：每个 section 最多返回 N 条（工业常规做法，用于提升结果多样性）
        per_section_limit = 2
        section_counts = {}
        filtered_similarities = []
        for doc_emb, similarity in similarities:
            sec = (doc_emb.section or "").strip() or "(no_section)"
            count = section_counts.get(sec, 0)
            if count >= per_section_limit:
                continue
            section_counts[sec] = count + 1
            filtered_similarities.append((doc_emb, similarity))
            if len(filtered_similarities) >= int(request.top_k or 10):
                break
        
        # 构建响应
        results = []
        for doc_emb, similarity in filtered_similarities:
            result = DocumentSearchResult(
                id=doc_emb.id,
                doc_type=doc_emb.doc_type,
                doc_subject=doc_emb.doc_subject,
                source_name=getattr(doc_emb, "source_name", None),
                section=getattr(doc_emb, "section", None),
                chunk_index=getattr(doc_emb, "chunk_index", None),
                similarity=similarity,
                embedding_content=doc_emb.content[:100] + "..." if doc_emb.content and len(doc_emb.content) > 100 else (doc_emb.content or doc_emb.doc_subject)
            )
            results.append(result)
        
        response = DocumentSearchResponse(
            success=True,
            results=results,
            query=request.query,
            org_code=request.org_code
        )
        
        logger.info(f"文档搜索完成，返回 {len(results)} 个结果")
        return response
        
    except Exception as e:
        logger.error(f"搜索文档时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索文档失败: {str(e)}")
