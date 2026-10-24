"""Chroma 向量库服务。"""

from __future__ import annotations

from langchain_chroma import Chroma

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


if __name__ == "__main__":
    from langchain_community.embeddings import DashScopeEmbeddings

    config.ensure_dashscope_api_key()
    retriever = VectorStoreService(
        DashScopeEmbeddings(model=config.embedding_model_name)
    ).get_retriever()
    results = retriever.invoke("工业离心风机设备参数")
    for result in results:
        print(result.page_content)
