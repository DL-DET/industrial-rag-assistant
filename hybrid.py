"""BM25 + 向量混合检索。

BM25 负责字面匹配，向量检索负责语义匹配；两路结果用 RRF 融合。
"""

from __future__ import annotations

import re
from typing import Iterable

import jieba
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

import config_data as config
from vector_stores import VectorStoreService


_TOKEN_PATTERN = re.compile(r"^[0-9a-z一-鿿]+$")
_STOPWORDS = {
    "的",
    "了",
    "是",
    "在",
    "和",
    "与",
    "及",
    "或",
    "有",
    "为",
    "对",
    "中",
    "上",
    "下",
    "如何",
    "什么",
    "哪些",
    "多少",
    "怎么",
    "需要",
    "应该",
}


def tokenize(text: str) -> list[str]:
    """中文分词并清洗，供 BM25 使用。"""
    tokens: list[str] = []
    for token in jieba.lcut(text.lower()):
        token = token.strip()
        if not token or token in _STOPWORDS:
            continue
        if _TOKEN_PATTERN.fullmatch(token):
            tokens.append(token)
    return tokens


def _document_key(document: Document) -> tuple[str, object, str]:
    """用于融合时去重；同一片段可能同时来自向量和 BM25。"""
    return (
        str(document.metadata.get("source", "")),
        document.metadata.get("page"),
        document.page_content,
    )


class BM25Index:
    def __init__(self, documents: list[Document]):
        self.documents = documents
        self.tokenized_documents = [tokenize(doc.page_content) for doc in documents]
        self.bm25 = (
            BM25Okapi(self.tokenized_documents) if self.tokenized_documents else None
        )

    def search(self, query: str, k: int) -> list[tuple[Document, float]]:
        if self.bm25 is None:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)
        ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
        return [
            (self.documents[index], float(score))
            for index, score in ranked[:k]
            if score > 0
        ]


def reciprocal_rank_fusion(
    ranked_lists: Iterable[list[tuple[Document, float]]],
    k: int = 60,
) -> list[tuple[Document, float]]:
    """RRF：只看排名，不比较不同检索器的原始分数。"""
    scores: dict[tuple[str, object, str], float] = {}
    documents: dict[tuple[str, object, str], Document] = {}
    for ranked in ranked_lists:
        for rank, (document, _) in enumerate(ranked, start=1):
            key = _document_key(document)
            documents.setdefault(key, document)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)

    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [(documents[key], score) for key, score in ordered]


class HybridRetriever:
    def __init__(
        self,
        vector_service: VectorStoreService,
        bm25_k: int | None = None,
        rrf_k: int | None = None,
    ):
        self.vector_service = vector_service
        self.bm25_k = bm25_k or config.hybrid_bm25_k
        self.rrf_k = rrf_k or config.hybrid_rrf_k
        self.documents = vector_service.all_documents()
        self.bm25 = BM25Index(self.documents)

    def search(self, query: str, k: int) -> list[tuple[Document, float]]:
        vector_results = self.vector_service.search_with_scores(query, k=k)
        bm25_results = self.bm25.search(query, k=self.bm25_k)

        if not bm25_results:
            return vector_results[:k]
        if not vector_results:
            return bm25_results[:k]
        return reciprocal_rank_fusion(
            [vector_results, bm25_results],
            k=self.rrf_k,
        )[:k]
