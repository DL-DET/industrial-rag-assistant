from langchain_core.documents import Document

from eval.metrics import (
    aggregate,
    first_relevant_rank,
    is_relevant,
    recall_at_k,
    reciprocal_rank,
)


def _item():
    return {
        "gold_sources": [{"file": "手册.pdf", "page": 5}],
        "gold_keywords": ["10MΩ", "绝缘电阻"],
    }


def test_is_relevant_requires_source_and_all_keywords():
    item = _item()

    assert is_relevant(
        Document(
            page_content="500V摇表测量绝缘电阻≥10MΩ",
            metadata={"source": "手册.pdf"},
        ),
        item,
    )
    assert not is_relevant(
        Document(
            page_content="500V摇表测量绝缘电阻≥10MΩ",
            metadata={"source": "其他.pdf"},
        ),
        item,
    )
    assert not is_relevant(
        Document(
            page_content="绝缘电阻要求",
            metadata={"source": "手册.pdf"},
        ),
        item,
    )


def test_first_relevant_rank_and_recall():
    item = _item()
    documents = [
        Document(page_content="无关内容", metadata={"source": "手册.pdf"}),
        Document(page_content="无关内容", metadata={"source": "手册.pdf"}),
        Document(
            page_content="绝缘电阻≥10MΩ",
            metadata={"source": "手册.pdf"},
        ),
    ]

    rank = first_relevant_rank(documents, item)

    assert rank == 3
    assert recall_at_k(rank, 1) == 0.0
    assert recall_at_k(rank, 3) == 1.0
    assert reciprocal_rank(rank) == 1 / 3


def test_aggregate_summary():
    records = [
        {
            "id": "q1",
            "answerable": True,
            "first_rank": 1,
            "top_score": 0.9,
            "latency_ms": 10.0,
        },
        {
            "id": "q2",
            "answerable": True,
            "first_rank": 4,
            "top_score": 0.5,
            "latency_ms": 20.0,
        },
        {
            "id": "u1",
            "answerable": False,
            "first_rank": None,
            "top_score": 0.3,
            "latency_ms": 30.0,
        },
    ]

    summary = aggregate(records)

    assert summary["answerable"] == 2
    assert summary["recall@1"] == 0.5
    assert summary["recall@3"] == 0.5
    assert summary["recall@5"] == 1.0
    assert summary["mrr"] == 0.625
    assert summary["unanswerable_top_score"]["avg"] == 0.3
    assert summary["latency_p50_ms"] == 20.0
    assert summary["latency_p95_ms"] == 30.0
