import os
import json
from typing import List, Dict, Tuple, Optional
import numpy as np
from pydantic import BaseModel
from pathlib import Path
import fitz  # PyMuPDF for PDF processing
from docx import Document as DocxDocument
import chardet
from core.logger import logger
from model.embedding_model import TextEmbeddingModel
from repository.entity.sql_entity import DocumentEmbedding
from config.config import settings
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import re
import hashlib


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    计算两个向量的余弦相似度
    """
    a = np.array(a)
    b = np.array(b)
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return float(dot_product / (norm_a * norm_b))


class DocumentProcessor:
    """
    文档处理器，负责文档解析、切分和向量化
    """
    
    def __init__(self, embedding_model: TextEmbeddingModel):
        self.embedding_model = embedding_model
        self.supported_types = {'.txt', '.pdf', '.doc', '.docx'}
    
    def read_document(self, file_path: str) -> str:
        """
        读取文档内容
        """
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext == '.txt':
            return self._read_txt(file_path)
        elif file_ext == '.pdf':
            return self._read_pdf(file_path)
        elif file_ext in ['.doc', '.docx']:
            return self._read_docx(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {file_ext}")
    
    def _read_txt(self, file_path: str) -> str:
        """
        读取TXT文件
        """
        # 尝试不同的编码方式
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                logger.info(f"使用 {encoding} 编码读取TXT文件成功")
                return content
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，使用chardet检测编码
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding']
        
        with open(file_path, 'r', encoding=encoding) as f:
            content = f.read()
        
        logger.info(f"使用检测到的 {encoding} 编码读取TXT文件成功")
        return content
    
    def _read_pdf(self, file_path: str) -> str:
        """
        读取PDF文件
        """
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            logger.error(f"读取PDF文件失败: {e}")
            raise
    
    def _read_docx(self, file_path: str) -> str:
        """
        读取DOCX文件
        """
        try:
            doc = DocxDocument(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs)
        except Exception as e:
            logger.error(f"读取DOCX文件失败: {e}")
            raise
    
    def split_document(self, content: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """
        将文档内容切分为多个块（更适合中文：先按章节标题分段，再按句子拼接；overlap 使用字符数）
        """
        # 兼容旧调用：只返回 chunk 文本列表
        grouped = self.split_document_grouped(content=content, chunk_size=chunk_size, overlap=overlap)
        return [item["content"] for item in grouped]

    def split_document_grouped(self, content: str, chunk_size: int = 512, overlap: int = 50) -> List[Dict[str, object]]:
        """
        工业级文本切分（不依赖大模型）：
        1) 清洗 & 归一化换行/空白
        2) 章节分组（section）
        3) 句子切分
        4) 装箱生成 chunk（长度控制 + 字符级 overlap）

        返回结构：[{"section": str, "chunk_index": int, "content": str}, ...]
        """
        if not content:
            return []

        # Step 1: 参数归一化（chunk_size / overlap 以“字符长度”近似控制）
        chunk_size = max(int(chunk_size), 50)
        overlap = max(int(overlap), 0)

        # Step 2: 先按标题/编号/分隔符分组为多个 section
        section_items = self._split_sections_with_titles(content)

        # Step 3: section 内按句子边界切分，并装箱成 chunk
        results: List[Dict[str, object]] = []

        for section_title, section_text in section_items:
            current_chunk = ""
            chunk_idx = 0

            def flush_current():
                nonlocal current_chunk, chunk_idx
                if current_chunk.strip():
                    results.append({
                        "section": section_title,
                        "chunk_index": chunk_idx,
                        "content": current_chunk.strip()
                    })
                    chunk_idx += 1
                current_chunk = ""

            sentences = self._split_cn_sentences(section_text)
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                # Step 3.1: 避免超长句子：硬切成小段（极少发生，属于兜底）
                if len(sentence) > chunk_size:
                    parts = [sentence[i:i + chunk_size] for i in range(0, len(sentence), chunk_size)]
                else:
                    parts = [sentence]

                for part in parts:
                    part = part.strip()
                    if not part:
                        continue

                    # Step 3.2: 装箱（packing）：把句子拼到 chunk_size 上限
                    separator = "\n" if current_chunk else ""
                    if len(current_chunk) + len(separator) + len(part) <= chunk_size:
                        current_chunk = f"{current_chunk}{separator}{part}" if current_chunk else part
                        continue

                    # Step 3.3: 当前块满了，先落盘
                    flush_current()

                    # Step 3.4: 新块携带 overlap（字符级），保证上下文连续
                    if overlap > 0 and results:
                        prev = results[-1]["content"]
                        prev_text = prev if isinstance(prev, str) else ""
                        overlap_text = prev_text[-overlap:] if len(prev_text) > overlap else prev_text
                        current_chunk = f"{overlap_text}\n{part}" if overlap_text else part
                    else:
                        current_chunk = part

            flush_current()

        return results

    def _split_sections(self, content: str) -> List[str]:
        # 兼容旧逻辑：返回纯文本 section 列表
        return [item[1] for item in self._split_sections_with_titles(content)]

    def _split_sections_with_titles(self, content: str) -> List[Tuple[str, str]]:
        """将全文分成多个 section，并尽量提取 section 标题（通用文本/文档做法）。"""
        lines = [re.sub(r"\s+", " ", ln).strip() for ln in content.splitlines()]
        lines = [ln for ln in lines if ln]

        heading_keywords = {
            "摘要", "目录", "前言", "引言", "概述", "背景", "结论", "附录",
            "简介", "说明", "注意事项", "常见问题", "FAQ",
            "译文", "赏析", "作者介绍", "作品评价",
            "写作手法", "艺术特色", "表现手法", "主题", "主旨", "内容介绍"
        }

        sentence_end_re = re.compile(r"[。！？!?；;：:]$")
        separator_re = re.compile(r"^[-=_*]{3,}$")

        def looks_like_heading_strict(line: str) -> bool:
            if not line:
                return False
            if separator_re.match(line):
                return True
            if len(line) <= 24 and any(k in line for k in heading_keywords):
                return True
            if re.match(r"^(第[一二三四五六七八九十0-9]+[章节篇部分])\s*\S+", line):
                return True
            if re.match(r"^\d+(?:\.\d+){0,4}[\.、．)）]?\s*\S+", line):
                return True
            if re.match(r"^[一二三四五六七八九十]+[、.．)）]\s*\S+", line):
                return True
            return False

        def is_heading(line: str) -> bool:
            if not line:
                return False
            if looks_like_heading_strict(line):
                return True
            # 通用短行标题启发式：短、无句末标点、相对“像标题”
            if len(line) <= 20 and not sentence_end_re.search(line):
                # 太像正文的短句（包含逗号太多）不当作标题
                if line.count("，") + line.count(",") >= 2:
                    return False
                # 有明显结构符号则更像标题
                if any(sym in line for sym in [":", "：", "-", "—"]):
                    return True
                # 纯短语也可视作标题
                return True
            return False

        # Step 1: 预处理：合并 PDF/拷贝文本常见的“硬换行断句”
        merged_lines: List[str] = []
        for line in lines:
            if not merged_lines:
                merged_lines.append(line)
                continue

            prev = merged_lines[-1]
            if (
                not looks_like_heading_strict(line)
                and not looks_like_heading_strict(prev)
                and not sentence_end_re.search(prev)
                and len(prev) < 80
                and len(line) < 80
            ):
                merged_lines[-1] = f"{prev} {line}".strip()
            else:
                merged_lines.append(line)

        lines = merged_lines

        # Step 2: 章节分组（section）：遇到标题行则开启新 section
        section_items: List[Tuple[str, List[str]]] = []
        current_title = ""
        buf: List[str] = []

        def flush_section():
            nonlocal buf, current_title
            if not buf:
                return
            # 默认标题：使用第一行的前 20 字作为兜底（便于后续聚合）
            title = current_title.strip() or (buf[0][:20] if buf[0] else "")
            section_items.append((title, buf))
            buf = []

        for line in lines:
            if is_heading(line):
                # 遇到新的标题前，先把上一 section 刷出
                if buf:
                    flush_section()
                current_title = line
                # 标题只作为 section 元数据，不进入正文内容，避免产生仅标题的 chunk
                buf = []
                continue

            buf.append(line)

        flush_section()

        # Step 3: 输出 section 文本：标题 + 内容合并为一个 text 块
        return [(title, "\n".join(sec_lines).strip()) for title, sec_lines in section_items]

    def _split_cn_sentences(self, text: str) -> List[str]:
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return []

        # 以中文/英文句末标点切分，并保留标点
        parts = re.split(r"([。！？!?；;])", text)
        sentences: List[str] = []
        for i in range(0, len(parts), 2):
            seg = parts[i].strip() if i < len(parts) else ""
            punct = parts[i + 1] if i + 1 < len(parts) else ""
            s = f"{seg}{punct}".strip()
            if s:
                sentences.append(s)
        return sentences
    
    def _split_long_paragraph(self, text: str, max_length: int) -> List[str]:
        """
        将长段落按句子切分
        """
        import re
        # 按句子边界切分
        sentences = re.split(r'([。！？!?]+)', text)
        # 将标点符号和句子内容配对
        sentence_list = []
        for i in range(0, len(sentences)-1, 2):
            if i+1 < len(sentences):
                sentence_list.append(sentences[i] + sentences[i+1])
            else:
                sentence_list.append(sentences[i])
        
        # 合并较短的句子以达到合适的长度
        merged_sentences = []
        current_sentence = ""
        
        for sentence in sentence_list:
            if len(current_sentence + sentence) < max_length:
                current_sentence += sentence
            else:
                if current_sentence.strip():
                    merged_sentences.append(current_sentence.strip())
                current_sentence = sentence
        
        if current_sentence.strip():
            merged_sentences.append(current_sentence.strip())
        
        return merged_sentences
    
    def _get_overlap_text(self, chunk: str, overlap_size: int) -> str:
        """
        获取块的末尾部分作为重叠文本
        """
        words = chunk.split()
        if len(words) <= overlap_size:
            return chunk + " "
        
        overlap_words = words[-overlap_size:]
        return " ".join(overlap_words) + " "


class DocumentEmbeddingService:
    """
    文档向量服务类
    """
    
    def __init__(self, db_session: Session, embedding_model: TextEmbeddingModel):
        # 修复：确保正确使用数据库会话
        self.db = db_session
        self.document_processor = DocumentProcessor(embedding_model)
        self.embedding_model = embedding_model

    def _coerce_embedding_vector(self, embedding_value) -> Optional[List[float]]:
        """兼容数据库中 embedding 可能为 JSON 数组或 JSON 字符串两种格式"""
        if embedding_value is None:
            return None
        if isinstance(embedding_value, list):
            return embedding_value
        if isinstance(embedding_value, str):
            try:
                parsed = json.loads(embedding_value)
                return parsed if isinstance(parsed, list) else None
            except Exception:
                return None
        return None
    
    def process_and_save_document(
        self, 
        file_path: str, 
        doc_type: str, 
        doc_subject: str, 
        org_code: str,
        chunk_size: int = 512,
        overlap: int = 50
    ) -> List[DocumentEmbedding]:
        """
        处理文档并保存向量到数据库
        """
        # Step 1: 读取文档内容（txt/pdf/docx）
        content = self.document_processor.read_document(file_path)

        # Step 2: 分组切分（section/chunk_index），生成稳定的 chunk 单元
        grouped_chunks = self.document_processor.split_document_grouped(content, chunk_size, overlap)

        # Step 3: 去重准备：基于归一化文本计算 SHA256（工业常规做法）
        def normalize_for_hash(text: str) -> str:
            text = re.sub(r"\s+", " ", text or "").strip()
            return text

        source_name = Path(file_path).name
        seen_hashes: set[str] = set()
        to_insert: List[DocumentEmbedding] = []

        # Step 4: 对每个 chunk 生成向量并构建入库对象（先构建列表，最后批量写库）
        for item in grouped_chunks:
            chunk = str(item.get("content", "") or "").strip()
            if not chunk:
                continue

            normalized = normalize_for_hash(chunk)
            content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            if content_hash in seen_hashes:
                continue
            seen_hashes.add(content_hash)

            # Step 4.1: 生成 embedding（此处使用 embedding 模型，不需要对话大模型）
            result = self.embedding_model.get_embedding_vector(chunk)
            if not result:
                logger.error(f"生成向量失败，内容: {chunk[:100]}...")
                continue

            # Step 4.2: 构建 ORM 对象，写入 section/chunk_index/source_name/content_hash
            to_insert.append(
                DocumentEmbedding(
                    doc_type=doc_type,
                    doc_subject=doc_subject,
                    source_name=source_name,
                    org_code=org_code,
                    section=str(item.get("section", "") or ""),
                    chunk_index=int(item.get("chunk_index", 0) or 0),
                    embedding=result,
                    content=chunk,
                    content_hash=content_hash
                )
            )

        # Step 5: 批量入库（比逐条 commit 快很多，生产常规）
        try:
            if to_insert:
                self.db.add_all(to_insert)
                self.db.commit()
                for obj in to_insert:
                    try:
                        self.db.refresh(obj)
                    except Exception:
                        pass
            return to_insert
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存文档向量到数据库失败: {e}")
            raise
    
    def search_similar_documents(
        self, 
        query: str, 
        org_code: str, 
        top_k: int = 10
    ) -> List[Tuple[DocumentEmbedding, float]]:
        """
        根据查询内容搜索相似文档
        """
        # 1. 生成查询向量
        query_vector = self.embedding_model.get_embedding_vector(query)
        if not query_vector:
            logger.error("生成查询向量失败")
            return []
        
        # 2. 从数据库获取所有相关文档向量
        # 修复：确保 self.db 是正确的数据库会话
        doc_embeddings = self.db.query(DocumentEmbedding).filter(
            DocumentEmbedding.org_code == org_code
        ).all()
        
        # 3. 计算相似度
        similarities = []
        for doc_emb in doc_embeddings:
            try:
                stored_vector = self._coerce_embedding_vector(doc_emb.embedding)
                if not stored_vector:
                    logger.error(f"解析数据库向量失败, 文档ID: {doc_emb.id}")
                    continue
                similarity = cosine_similarity(query_vector, stored_vector)
                similarities.append((doc_emb, similarity))
            except Exception as e:
                logger.error(f"计算相似度失败: {e}, 文档ID: {doc_emb.id}")
                continue
        
        # 4. 按相似度排序并返回top_k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
