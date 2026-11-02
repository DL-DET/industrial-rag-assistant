"""运行检索基线评测。

用法：
    python -m eval.run_eval

只调用 Embedding（不调用问答模型），因此成本低、速度快，适合每次
检索策略改动后跑回归。
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_community.embeddings import DashScopeEmbeddings

import config_data as config
from eval.metrics import (
    aggregate,
    first_relevant_rank,
    recall_at_k,
    reciprocal_rank,
)
from vector_stores import VectorStoreService


EVAL_TOP_K = 10
BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "dataset.jsonl"
RESULTS_PATH = BASE_DIR / "results.jsonl"
REPORT_PATH = BASE_DIR / "report.md"


def load_dataset() -> list[dict[str, Any]]:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"评测集不存在：{DATASET_PATH}")

    items = [
        json.loads(line)
        for line in DATASET_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not items:
        raise ValueError("评测集为空")
    return items


def _preview(text: str, limit: int = 100) -> str:
    return " ".join(text.split())[:limit]


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _render_report(summary: dict[str, Any], records: list[dict[str, Any]]) -> str:
    lines = [
        "# RAG 检索基线报告",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 评测集：{summary['total']} 条（有答案 {summary['answerable']} / 无答案 {summary['unanswerable']}）",
        f"- 评测检索深度：top-{EVAL_TOP_K}",
        "- 相关性判定：来源文件属于 gold 文件，且正文命中全部 gold 关键词",
        "- 说明：同一资料同时存在 DOCX 与 PDF，关键词匹配避免等价来源被误判",
        "",
        "## 汇总",
        "",
        "| 指标 | 数值 |",
        "| --- | --- |",
        f"| recall@1 | {_fmt(summary['recall@1'])} |",
        f"| recall@3 | {_fmt(summary['recall@3'])} |",
        f"| recall@5 | {_fmt(summary['recall@5'])} |",
        f"| MRR | {_fmt(summary['mrr'])} |",
        f"| P50 检索延迟 | {_fmt(summary['latency_p50_ms'], 1)} ms |",
        f"| P95 检索延迟 | {_fmt(summary['latency_p95_ms'], 1)} ms |",
        "",
        "## Top-1 分数分布（用于 Day 2 阈值）",
        "",
        "| 组 | 平均 | 最小 | 最大 |",
        "| --- | --- | --- | --- |",
        f"| 有答案 | {_fmt(summary['answerable_top_score']['avg'])} | {_fmt(summary['answerable_top_score']['min'])} | {_fmt(summary['answerable_top_score']['max'])} |",
        f"| 无答案 | {_fmt(summary['unanswerable_top_score']['avg'])} | {_fmt(summary['unanswerable_top_score']['min'])} | {_fmt(summary['unanswerable_top_score']['max'])} |",
        "",
        "## 未命中",
        "",
        "、".join(summary["misses"]) if summary["misses"] else "无",
        "",
        "## 逐题结果",
        "",
        "| ID | 问题 | 类别 | 首次命中排名 | Top-1 来源 | 页码 | 分数 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for record in records:
        lines.append(
            f"| {record['id']} | {record['question']} | {record['category']} | "
            f"{'—' if record['first_rank'] is None else record['first_rank']} | "
            f"{record['top_source'] or '—'} | "
            f"{record['top_page'] if record['top_page'] is not None else '—'} | "
            f"{_fmt(record['top_score'])} |"
        )

    return "\n".join(lines) + "\n"


def run() -> dict[str, Any]:
    items = load_dataset()
    service = VectorStoreService(
        DashScopeEmbeddings(model=config.embedding_model_name)
    )
    records: list[dict[str, Any]] = []

    for item in items:
        started = time.perf_counter()
        pairs = service.search_with_scores(item["question"], k=EVAL_TOP_K)
        latency_ms = (time.perf_counter() - started) * 1000

        documents = [document for document, _ in pairs]
        scores = [float(score) for _, score in pairs]
        rank = first_relevant_rank(documents, item) if item["answerable"] else None
        top_document = documents[0] if documents else None

        record = {
            "id": item["id"],
            "question": item["question"],
            "category": item.get("category", ""),
            "answerable": item["answerable"],
            "first_rank": rank,
            "recall@1": recall_at_k(rank, 1) if item["answerable"] else None,
            "recall@3": recall_at_k(rank, 3) if item["answerable"] else None,
            "recall@5": recall_at_k(rank, 5) if item["answerable"] else None,
            "mrr": reciprocal_rank(rank) if item["answerable"] else None,
            "top_score": round(scores[0], 4) if scores else None,
            "top_source": top_document.metadata.get("source") if top_document else None,
            "top_page": top_document.metadata.get("page") if top_document else None,
            "latency_ms": round(latency_ms, 2),
            "retrieved": [
                {
                    "source": document.metadata.get("source"),
                    "page": document.metadata.get("page"),
                    "score": round(score, 4),
                    "preview": _preview(document.page_content),
                }
                for document, score in pairs
            ],
        }
        records.append(record)
        print(
            f"{item['id']} rank={rank} "
            f"top_score={record['top_score']} "
            f"latency={record['latency_ms']}ms"
        )

    summary = aggregate(records)
    RESULTS_PATH.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records),
        encoding="utf-8",
    )
    REPORT_PATH.write_text(_render_report(summary, records), encoding="utf-8")

    return {
        "summary": summary,
        "report": str(REPORT_PATH),
        "results": str(RESULTS_PATH),
    }


if __name__ == "__main__":
    result = run()
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
