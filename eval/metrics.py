"""检索评测指标。

这里刻意不用“来源文件 + 页码”直接判相关，因为同一套资料同时存在
DOCX 和 PDF：正文等价，但一个没有页码、一个有页码。统一用
「来源文件在 gold 列表中 + 正文命中 gold 关键词」判定，避免误杀等价来源。
"""

from __future__ import annotations

from typing import Any

from langchain_core.documents import Document


def is_relevant(document: Document, item: dict[str, Any]) -> bool:
    """检索片段是否命中评测项的依据。"""
    gold_files = {source["file"] for source in item.get("gold_sources", [])}
    if document.metadata.get("source") not in gold_files:
        return False

    keywords = item.get("gold_keywords", [])
    if not keywords:
        return True
    return all(keyword in document.page_content for keyword in keywords)


def first_relevant_rank(documents: list[Document], item: dict[str, Any]) -> int | None:
    """返回第一条相关片段的排名（从 1 开始），没有命中返回 None。"""
    for rank, document in enumerate(documents, start=1):
        if is_relevant(document, item):
            return rank
    return None


def recall_at_k(rank: int | None, k: int) -> float:
    """Top-k 内是否至少命中一条相关片段。"""
    return 1.0 if rank is not None and rank <= k else 0.0


def reciprocal_rank(rank: int | None) -> float:
    """第一条相关片段的倒数排名。"""
    return 1.0 / rank if rank else 0.0


def _stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"avg": None, "min": None, "max": None}
    return {
        "avg": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
    }


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((percentile / 100) * (len(ordered) - 1))
    index = max(0, min(index, len(ordered) - 1))
    return ordered[index]


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    """汇总逐题结果。"""
    answerable = [record for record in records if record["answerable"]]
    unanswerable = [record for record in records if not record["answerable"]]

    def mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    answerable_scores = [
        record["top_score"]
        for record in answerable
        if record.get("top_score") is not None
    ]
    unanswerable_scores = [
        record["top_score"]
        for record in unanswerable
        if record.get("top_score") is not None
    ]
    latencies = [
        record["latency_ms"]
        for record in records
        if record.get("latency_ms") is not None
    ]

    return {
        "total": len(records),
        "answerable": len(answerable),
        "unanswerable": len(unanswerable),
        "recall@1": mean(
            [recall_at_k(record["first_rank"], 1) for record in answerable]
        ),
        "recall@3": mean(
            [recall_at_k(record["first_rank"], 3) for record in answerable]
        ),
        "recall@5": mean(
            [recall_at_k(record["first_rank"], 5) for record in answerable]
        ),
        "mrr": mean([reciprocal_rank(record["first_rank"]) for record in answerable]),
        "misses": [
            record["id"] for record in answerable if record["first_rank"] is None
        ],
        "answerable_top_score": _stats(answerable_scores),
        "unanswerable_top_score": _stats(unanswerable_scores),
        "latency_p50_ms": _percentile(latencies, 50),
        "latency_p95_ms": _percentile(latencies, 95),
    }
