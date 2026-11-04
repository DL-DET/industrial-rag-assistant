"""答案级评测指标：关键词覆盖、引用、拒答和阈值扫描。"""

from __future__ import annotations

import re
from typing import Any

REFUSAL_MARKERS = (
    "知识库中暂无足够依据",
    "暂无足够依据",
    "没有足够依据",
    "资料不足",
)


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text)


def keyword_coverage(answer: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    content = normalize(answer)
    hits = sum(1 for keyword in keywords if normalize(keyword) in content)
    return hits / len(keywords)


def is_refusal(answer: str) -> bool:
    return any(marker in answer for marker in REFUSAL_MARKERS)


def evaluate_answer(
    item: dict[str, Any],
    answer: str,
    sources: list[str],
) -> dict[str, Any]:
    refusal = is_refusal(answer)
    if not item["answerable"]:
        return {
            "answerable": False,
            "refusal": refusal,
            "coverage": None,
            "all_keywords": None,
            "source_hit": None,
            "cites_source": None,
        }

    keywords = item.get("gold_keywords", [])
    gold_files = [
        source["file"] for source in item.get("gold_sources", []) if source.get("file")
    ]
    coverage = keyword_coverage(answer, keywords)
    return {
        "answerable": True,
        "refusal": refusal,
        "coverage": coverage,
        "all_keywords": coverage >= 1.0,
        "source_hit": any(
            gold_file in " ".join(sources) for gold_file in gold_files
        ),
        "cites_source": any(gold_file in answer for gold_file in gold_files),
    }


def threshold_table(
    records: list[dict[str, Any]],
    thresholds: list[float],
) -> list[dict[str, Any]]:
    answerable = [record for record in records if record["answerable"]]
    unanswerable = [record for record in records if not record["answerable"]]
    rows: list[dict[str, Any]] = []
    for threshold in thresholds:
        false_refusal = sum(
            1
            for record in answerable
            if record.get("top_score") is not None
            and record["top_score"] < threshold
        )
        correct_refusal = sum(
            1
            for record in unanswerable
            if record.get("top_score") is not None
            and record["top_score"] < threshold
        )
        rows.append(
            {
                "threshold": threshold,
                "answerable_false_refusal_rate": (
                    false_refusal / len(answerable) if answerable else 0.0
                ),
                "unanswerable_refusal_rate": (
                    correct_refusal / len(unanswerable) if unanswerable else 0.0
                ),
            }
        )
    return rows
