"""DashScope 文本重排服务。

向量检索负责召回候选，重排模型负责把“真正回答问题的片段”排到前面。
"""

from __future__ import annotations

from langchain_core.documents import Document

from dashscope import TextReRank

import config_data as config


class RerankService:
    def __init__(self, model: str | None = None):
        self.model = model or config.rerank_model

    def rerank(
        self,
        query: str,
        documents: list[Document],
        top_n: int | None = None,
    ) -> list[tuple[Document, float]]:
        """按问题相关性重排文档，返回 (文档, 重排分数) 列表。"""
        if not documents:
            return []

        response = TextReRank.call(
            model=self.model,
            query=query,
            documents=[document.page_content for document in documents],
            return_documents=False,
            top_n=top_n,
        )

        if getattr(response, "status_code", None) != 200:
            raise RuntimeError(
                f"重排失败：{getattr(response, 'code', None)} "
                f"{getattr(response, 'message', None)}"
            )

        results = getattr(getattr(response, "output", None), "results", None) or []
        reranked: list[tuple[Document, float]] = []
        for item in results:
            index = int(item["index"])
            score = float(item["relevance_score"])
            if 0 <= index < len(documents):
                reranked.append((documents[index], score))
        return reranked
