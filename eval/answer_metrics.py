"""答案级评测指标：关键词覆盖、引用、拒答和阈值扫描。"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

REFUSAL_MARKERS = (
    "知识库中暂无足够依据",
    "暂无足够依据",
    "没有足够依据",
    "资料不足",
)

# 同一单位的不同写法，统一成一种，避免“5毫米”和“5 mm”被判成不同。
UNIT_ALIASES = (
    ("毫米", "mm"),
    ("厘米", "cm"),
    ("千米", "km"),
    ("米每秒", "m/s"),
    ("吨每小时", "t/h"),
    ("千瓦", "kw"),
    ("兆帕", "mpa"),
)

# 关键词相邻两个字之间可能出现的虚词，例如“叶轮腐蚀”对应“叶轮是否有腐蚀”。
# 只在构造匹配正则时跳过，不从文本里直接删除，避免破坏关键词本身。
FILLER_WORDS = ("是否", "的", "进行", "大约", "左右", "有")


def normalize(text: str) -> str:
    """评测匹配前的文本归一化。

    只做确定性的等价变换：全角转半角、小写、去空白、单位统一。
    不用模糊或语义匹配：宁可留下少量假阴性，也不能让假阳性污染指标。
    """
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"\s+", "", text)
    for alias, canonical in UNIT_ALIASES:
        text = text.replace(alias, canonical)
    return text


def _keyword_pattern(keyword: str) -> re.Pattern[str]:
    """允许关键词的字之间夹虚词，例如“叶轮腐蚀”匹配“叶轮是否有腐蚀”。"""
    filler = "|".join(re.escape(word) for word in FILLER_WORDS)
    gap = f"(?:{filler})*"
    return re.compile(gap.join(re.escape(char) for char in keyword))


def keyword_coverage(answer: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    content = normalize(answer)
    hits = sum(
        1 for keyword in keywords if _keyword_pattern(normalize(keyword)).search(content)
    )
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
