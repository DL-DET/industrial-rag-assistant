"""运行检索基线评测。

用法：
    python -m eval.run_eval

只调用 Embedding（不调用问答模型），因此成本低、速度快，适合每次
检索策略改动后跑回归。
"""

from __future__ import annotations

import argparse
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
from hybrid import HybridRetriever, reciprocal_rank_fusion
from query_decompose import decompose_question
from rerank import RerankService
from vector_stores import VectorStoreService


EVAL_TOP_K = 10
BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "dataset.jsonl"
RESULTS_PATH = BASE_DIR / "results.jsonl"
REPORT_PATH = BASE_DIR / "report.md"


def load_dataset(dataset_path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    if not dataset_path.exists():
        raise FileNotFoundError(f"评测集不存在：{dataset_path}")

    items = [
        json.loads(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
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


def _render_report(
    summary: dict[str, Any],
    records: list[dict[str, Any]],
    label: str | None = None,
    rerank: bool = False,
    dataset_path: Path = DATASET_PATH,
    hybrid: bool = False,
    decompose: bool = False,
) -> str:
    retrieval_strategy = "向量 + BM25" if hybrid else "纯向量"
    if decompose:
        retrieval_strategy = f"查询拆解 + {retrieval_strategy}"
    if rerank:
        retrieval_strategy += " + 重排"
    lines = [
        "# RAG 检索评测报告",
        "",
        f"- 实验标签：{label or 'baseline'}",
        f"- 评测集文件：{dataset_path.name}",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 检索策略：{retrieval_strategy}",
        f"- 是否拆解：{'是' if decompose else '否'}",
        f"- 重排模型：{config.rerank_model if rerank else '—'}",
        f"- 评测集：{summary['total']} 条（有答案 {summary['answerable']} / 无答案 {summary['unanswerable']}）",
        f"- 评测检索深度：top-{EVAL_TOP_K}",
        "- 相关性判定：来源文件属于 gold 文件，且正文命中全部 gold 关键词",
        "- 说明：匹配前去除正文和关键词中的空白，避免 PDF 换行导致假阴性",
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
        f"## Top-1 {'重排' if rerank else ('融合' if hybrid else '相似度')}分数分布（用于阈值）",
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


def run(
    label: str | None = None,
    rerank: bool = False,
    dataset_path: Path = DATASET_PATH,
    hybrid: bool = False,
    decompose: bool = False,
    rerank_top_n: int | None = None,
) -> dict[str, Any]:
    items = load_dataset(dataset_path)
    service = VectorStoreService(
        DashScopeEmbeddings(model=config.embedding_model_name)
    )
    hybrid_retriever = HybridRetriever(service) if hybrid else None
    reranker = RerankService() if rerank else None
    records: list[dict[str, Any]] = []
    report_path = BASE_DIR / (f"report_{label}.md" if label else REPORT_PATH.name)
    results_path = BASE_DIR / (f"results_{label}.jsonl" if label else RESULTS_PATH.name)

    for item in items:
        started = time.perf_counter()
        queries = decompose_question(item["question"]) if decompose else [item["question"]]
        query_results = []
        for query in queries:
            if hybrid_retriever is not None:
                query_results.append(hybrid_retriever.search(query, k=EVAL_TOP_K))
            else:
                query_results.append(
                    service.search_with_scores(query, k=EVAL_TOP_K)
                )

        pairs = (
            reciprocal_rank_fusion(query_results)
            if len(query_results) > 1
            else query_results[0]
        )
        if reranker is not None:
            pairs = reranker.rerank(
                item["question"],
                [document for document, _ in pairs],
                top_n=rerank_top_n or EVAL_TOP_K,
            )
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
            "queries": queries,
            "score_kind": "_".join(
                part
                for part, enabled in [
                    ("decompose", decompose),
                    ("hybrid", hybrid),
                    ("rerank", rerank),
                ]
                if enabled
            )
            or "vector",
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
    results_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records),
        encoding="utf-8",
    )
    report_path.write_text(
        _render_report(
            summary,
            records,
            label=label,
            rerank=rerank,
            dataset_path=dataset_path,
            hybrid=hybrid,
            decompose=decompose,
        ),
        encoding="utf-8",
    )

    return {
        "summary": summary,
        "report": str(report_path),
        "results": str(results_path),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行 RAG 检索评测")
    parser.add_argument(
        "--label",
        default=None,
        help="实验标签，例如 split300；不填则写入基线 report.md",
    )
    parser.add_argument(
        "--rerank",
        action="store_true",
        help="在向量召回 top-10 后使用 DashScope 重排",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="评测集路径，默认 eval/dataset.jsonl",
    )
    parser.add_argument(
        "--hybrid",
        action="store_true",
        help="使用 BM25 + 向量 RRF 混合检索",
    )
    parser.add_argument(
        "--decompose",
        action="store_true",
        help="对多部分问题做规则拆解，再融合子查询结果",
    )
    parser.add_argument(
        "--rerank-top-n",
        type=int,
        default=None,
        help="重排后保留条数，默认等于评测深度 top-10",
    )
    args = parser.parse_args()
    label_parts = []
    if args.decompose:
        label_parts.append("decompose")
    if args.hybrid:
        label_parts.append("hybrid")
    if args.rerank:
        label_parts.append("rerank")
    label = args.label or ("_".join(label_parts) or None)
    dataset_path = Path(args.dataset).resolve() if args.dataset else DATASET_PATH
    result = run(
        label=label,
        rerank=args.rerank,
        dataset_path=dataset_path,
        hybrid=args.hybrid,
        decompose=args.decompose,
        rerank_top_n=args.rerank_top_n,
    )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"report : {result['report']}")
    print(f"results: {result['results']}")
