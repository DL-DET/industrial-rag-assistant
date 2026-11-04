"""读取 logs/qa.jsonl，输出查询量、失败率和延迟分位数。"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((p / 100) * (len(ordered) - 1))
    return ordered[max(0, min(index, len(ordered) - 1))]


def main() -> None:
    parser = argparse.ArgumentParser(description="统计 RAG 查询 trace")
    parser.add_argument("--log", default="logs/qa.jsonl")
    args = parser.parse_args()

    path = Path(args.log)
    if not path.exists():
        print(f"日志不存在：{path}")
        return

    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not records:
        print("日志为空")
        return

    total = len(records)
    statuses = Counter(record.get("rerank_status", "unknown") for record in records)
    fallback = sum(1 for record in records if record.get("fallback"))
    refused = sum(1 for record in records if record.get("refused"))
    candidates = [record["candidate_count"] for record in records]
    returned = [record["returned_count"] for record in records]

    def values(field: str) -> list[float]:
        return [
            record[field]
            for record in records
            if record.get(field) is not None
        ]

    print(f"查询总数：{total}")
    print("重排状态：" + "，".join(f"{key}={value}" for key, value in statuses.items()))
    print(f"fallback：{fallback} 次，{fallback / total:.1%}")
    print(f"拒答：{refused} 次，{refused / total:.1%}")
    print(f"平均候选数：{sum(candidates) / total:.1f}")
    print(f"平均返回数：{sum(returned) / total:.1f}")

    for label, field in [
        ("检索", "retrieval_ms"),
        ("重排", "rerank_ms"),
        ("生成", "generation_ms"),
    ]:
        series = values(field)
        p50 = percentile(series, 50)
        p95 = percentile(series, 95)
        if p50 is None:
            print(f"{label}耗时：无数据")
        else:
            print(f"{label}耗时：P50={p50:.1f}ms P95={p95:.1f}ms")

    sources = Counter(
        source
        for record in records
        for source in record.get("top_sources", [])
    )
    if sources:
        print("Top 来源：")
        for source, count in sources.most_common(5):
            print(f"  {count} 次 | {source}")


if __name__ == "__main__":
    main()
