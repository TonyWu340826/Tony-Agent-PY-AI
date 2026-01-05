from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
import asyncio
import os
from dto.embedding_model import EmbeddingRequest, EmbeddingResponse, EmbeddingItem, DocumentSearchRequest, DocumentSearchResponse, DocumentSearchResult
from model import get_embedding_model, TextEmbeddingModel
from core.logger import logger
from Embedding.document_embedding_model import DocumentEmbeddingService
from sqlalchemy.orm import Session
from core.dependencies import get_db


# 创建路由
router = APIRouter()


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
        similarities = doc_service.search_similar_documents(
            request.query, request.org_code, request.top_k
        )
        
        # 构建响应
        results = []
        for doc_emb, similarity in similarities:
            result = DocumentSearchResult(
                id=doc_emb.id,
                doc_type=doc_emb.doc_type,
                doc_subject=doc_emb.doc_subject,
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
