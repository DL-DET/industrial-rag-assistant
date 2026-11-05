"""知识库写入服务。"""

from __future__ import annotations

import hashlib
import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config_data as config
from chunking import build_parent_child_documents


logger = logging.getLogger(__name__)

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


def drop_md5(md5_str: str) -> None:
    """移除内容指纹。

    删除资料时必须同步清理，否则向量已经删掉、指纹还在，
    重新上传同一份文件会被 check_md5 判成“已存在”跳过，资料再也加不回来。
    """
    md5_path = Path(config.md5_path)
    if not md5_path.exists():
        return

    lines = [line.strip() for line in md5_path.read_text(encoding="utf-8").splitlines()]
    kept = [line for line in lines if line and line != md5_str]
    if len(kept) == len([line for line in lines if line]):
        return

    md5_path.write_text(
        "\n".join(kept) + ("\n" if kept else ""),
        encoding="utf-8",
    )


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

    def _source_state(self, filename: str) -> tuple[list[str], int]:
        """返回某个来源的现有向量 ids 和最大版本号。"""
        data = self.chroma.get(
            where={"source": filename},
            include=["metadatas"],
        )
        ids = data.get("ids") or []
        versions = [
            int(metadata.get("version", 0))
            for metadata in (data.get("metadatas") or [])
            if metadata
        ]
        return ids, max(versions, default=0)

    def list_documents(self) -> list[dict[str, object]]:
        """按 doc_id 汇总知识库中的资料，供上传页展示和删除。"""
        data = self.chroma.get(include=["metadatas"])
        grouped: dict[tuple[str, str], dict[str, object]] = {}
        for metadata in data.get("metadatas") or []:
            if not metadata:
                continue
            source = str(metadata.get("source", "未知来源"))
            doc_id = str(metadata.get("doc_id", ""))
            key = (source, doc_id)
            entry = grouped.setdefault(
                key,
                {
                    "source": source,
                    "doc_id": doc_id,
                    "version": int(metadata.get("version", 1)),
                    "updated_at": metadata.get("updated_at", ""),
                    "chunks": 0,
                },
            )
            entry["chunks"] = int(entry["chunks"]) + 1
            entry["version"] = max(
                int(entry["version"]),
                int(metadata.get("version", 1)),
            )
        return sorted(
            grouped.values(),
            key=lambda item: (str(item["source"]), -int(item["version"])),
        )

    def delete_by_source(self, filename: str) -> int:
        data = self.chroma.get(where={"source": filename})
        ids = data.get("ids") or []
        if not ids:
            return 0
        self.chroma.delete(ids=ids)
        # doc_id 当前就是内容指纹，删向量后要一起清掉，否则重新上传会被判重跳过。
        for metadata in data.get("metadatas") or []:
            if metadata and metadata.get("doc_id"):
                drop_md5(str(metadata["doc_id"]))
        return len(ids)

    def delete_by_doc_id(self, doc_id: str) -> int:
        data = self.chroma.get(where={"doc_id": doc_id})
        ids = data.get("ids") or []
        if not ids:
            return 0
        self.chroma.delete(ids=ids)
        drop_md5(doc_id)
        return len(ids)

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
            old_ids, old_version = self._source_state(filename)
            documents = build_parent_child_documents(
                text=data,
                source=filename,
                doc_id=md5_hex,
                create_time=create_time,
                version=old_version + 1,
                updated_at=create_time,
                child_splitter=self.splitter,
                parent_splitter=self.parent_splitter,
            )
            if not documents:
                raise ValueError("文本分块结果为空，未写入知识库")

            new_ids = self.chroma.add_texts(
                [document.page_content for document in documents],
                metadatas=[document.metadata for document in documents],
            )
            try:
                save_md5(md5_hex)
            except Exception:
                # 向量已写入但状态保存失败：回滚本次写入，避免留下无法去重的数据。
                if new_ids:
                    self.chroma.delete(ids=new_ids)
                raise

            if old_ids:
                try:
                    self.chroma.delete(ids=old_ids)
                except Exception:
                    logger.warning(
                        "旧版本向量删除失败：source=%s ids=%s",
                        filename,
                        old_ids,
                        exc_info=True,
                    )

        return IngestResult(
            status="success",
            chunks=len(documents),
            message=(
                f"[成功] 已将 {len(documents)} 个文本片段写入知识库"
                f"（版本 {old_version + 1}）"
            ),
        )


if __name__ == "__main__":
    service = KnowledgeBaseService()
    print(service.upload_by_str("工业离心风机", "testfile").message)
