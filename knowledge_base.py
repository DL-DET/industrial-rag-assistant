"""知识库写入服务。"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config_data as config
from chunking import build_parent_child_documents, split_text_by_page


# Streamlit 可能并发触发上传请求，加锁可以避免同一内容被重复写入。
_INGEST_LOCK = threading.Lock()


@dataclass(frozen=True)
class IngestResult:
    """一次入库操作的结构化结果，供页面区分成功与跳过。"""

    status: str
    chunks: int
    message: str


def check_md5(md5_str: str) -> bool:
    """检查内容指纹是否已经写入过。"""
    md5_path = Path(config.md5_path)
    if not md5_path.exists():
        md5_path.parent.mkdir(parents=True, exist_ok=True)
        md5_path.touch()
        return False
    return md5_str in {
        line.strip() for line in md5_path.read_text(encoding="utf-8").splitlines()
    }


def save_md5(md5_str: str) -> None:
    """记录已写入内容，用于后续去重。"""
    md5_path = Path(config.md5_path)
    md5_path.parent.mkdir(parents=True, exist_ok=True)
    with md5_path.open("a", encoding="utf-8") as file:
        file.write(f"{md5_str}\n")


def get_string_md5(input_str: str, encoding: str = "utf-8") -> str:
    """计算内容指纹；这里仅用于去重，不用于安全校验。"""
    return hashlib.md5(
        input_str.encode(encoding=encoding),
        usedforsecurity=False,
    ).hexdigest()


class KnowledgeBaseService:
    def __init__(self):
        config.ensure_dashscope_api_key()
        config.persist_directory.mkdir(parents=True, exist_ok=True)
        self.chroma = Chroma(
            collection_name=config.collection_name,
            embedding_function=DashScopeEmbeddings(
                model=config.embedding_model_name
            ),
            persist_directory=str(config.persist_directory),
        )
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=config.separators,
            length_function=len,
        )
        self.parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.parent_chunk_size,
            chunk_overlap=config.parent_chunk_overlap,
            separators=config.separators,
            length_function=len,
        )

    def upload_by_str(self, data: str, filename: str) -> IngestResult:
        data = data.strip()
        if not data:
            raise ValueError("没有提取到可写入知识库的文本")

        md5_hex = get_string_md5(data)
        with _INGEST_LOCK:
            if check_md5(md5_hex):
                return IngestResult(
                    status="skipped",
                    chunks=0,
                    message="[跳过] 相同内容已存在于知识库中",
                )

            create_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            documents = build_parent_child_documents(
                text=data,
                source=filename,
                doc_id=md5_hex,
                create_time=create_time,
                child_splitter=self.splitter,
                parent_splitter=self.parent_splitter,
            )
            if not documents:
                raise ValueError("文本分块结果为空，未写入知识库")

            self.chroma.add_texts(
                [document.page_content for document in documents],
                metadatas=[document.metadata for document in documents],
            )
            save_md5(md5_hex)

        return IngestResult(
            status="success",
            chunks=len(documents),
            message=f"[成功] 已将 {len(documents)} 个文本片段写入知识库",
        )


if __name__ == "__main__":
    service = KnowledgeBaseService()
    print(service.upload_by_str("工业离心风机", "testfile").message)
