"""Chroma 向量库服务。"""

from __future__ import annotations

from langchain_chroma import Chroma
from langchain_core.documents import Document

import config_data as config


class VectorStoreService:
    def __init__(self, embedding):
        self.embedding = embedding
        config.persist_directory.mkdir(parents=True, exist_ok=True)
        self.vector_store = Chroma(
            collection_name=config.collection_name,
            embedding_function=self.embedding,
            persist_directory=str(config.persist_directory),
        )

    def get_retriever(self):
        """返回可直接接入 LangChain 链路的向量检索器。"""
        return self.vector_store.as_retriever(
            search_kwargs={"k": config.retrieval_top_k}
        )

    def search_with_scores(
        self,
        query: str,
        k: int | None = None,
    ) -> list[tuple[Document, float]]:
        """返回 (文档, 相关性分数)，供评测、阈值实验和 trace 使用。"""
        return self.vector_store.similarity_search_with_relevance_scores(
            query,
            k=k or config.retrieval_top_k,
        )

    def all_documents(self) -> list[Document]:
        """读取全量片段，供 BM25 等词法检索建索引。"""
        data = self.vector_store.get(include=["documents", "metadatas"])
        texts = data.get("documents") or []
        metadatas = data.get("metadatas") or []
        return [
            Document(page_content=text, metadata=metadata or {})
            for text, metadata in zip(texts, metadatas)
            if text
        ]


if __name__ == "__main__":
    from langchain_community.embeddings import DashScopeEmbeddings

    config.ensure_dashscope_api_key()
    retriever = VectorStoreService(
        DashScopeEmbeddings(model=config.embedding_model_name)
    ).get_retriever()
    results = retriever.invoke("工业离心风机设备参数")
    for result in results:
        print(result.page_content)
