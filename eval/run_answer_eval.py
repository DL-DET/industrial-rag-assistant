"""答案级评测：生成回答，检查关键词覆盖、引用和拒答。

默认只抽样一部分题目，避免一次消耗过多问答模型 token。
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import config_data as config
from citation import add_citations
from eval.answer_metrics import evaluate_answer, threshold_table
from eval.faithfulness import judge_faithfulness
from rag import REFUSAL_ANSWER, RagService, should_refuse


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET = BASE_DIR / "dataset_v2.jsonl"
DEFAULT_REPORT = BASE_DIR / "answer_report.md"
DEFAULT_RESULTS = BASE_DIR / "answer_results.jsonl"
THRESHOLDS = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]


def load_items(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def select_evenly(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    if limit >= len(items):
        return items
    if limit <= 0:
        return []
    step = len(items) / limit
    return [items[min(int(index * step), len(items) - 1)] for index in range(limit)]


def _preview(text: str, limit: int = 160) -> str:
    return " ".join(text.split())[:limit]


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [record for record in records if record["answerable"]]
    unanswerable = [record for record in records if not record["answerable"]]
    # 判定失败（faithful 为 None）的题不进入分母，避免污染忠实度指标。
    judged = [record for record in answerable if record.get("faithful") is not None]

    def mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    return {
        "answerable": len(answerable),
        "unanswerable": len(unanswerable),
        "coverage": mean(
            [record["coverage"] for record in answerable if record["coverage"] is not None]
        ),
        "all_keywords_rate": mean(
            [1.0 if record["all_keywords"] else 0.0 for record in answerable]
        ),
        "source_hit_rate": mean(
            [1.0 if record["source_hit"] else 0.0 for record in answerable]
        ),
        "cites_source_rate": mean(
            [1.0 if record["cites_source"] else 0.0 for record in answerable]
        ),
        "answerable_refusal_rate": mean(
            [1.0 if record["refusal"] else 0.0 for record in answerable]
        ),
        "unanswerable_refusal_rate": mean(
            [1.0 if record["refusal"] else 0.0 for record in unanswerable]
        ),
        "answerable_route_refusal_rate": mean(
            [1.0 if record["refusal_route"] else 0.0 for record in answerable]
        ),
        "unanswerable_route_refusal_rate": mean(
            [1.0 if record["refusal_route"] else 0.0 for record in unanswerable]
        ),
        "judged_count": len(judged),
        "faithful_rate": (
            mean([1.0 if record["faithful"] else 0.0 for record in judged])
            if judged
            else None
        ),
        "thresholds": threshold_table(records, THRESHOLDS),
    }


def render_report(summary: dict[str, Any], records: list[dict[str, Any]]) -> str:
    lines = [
        "# RAG 答案级评测报告",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 样本：有答案 {summary['answerable']} / 无答案 {summary['unanswerable']}",
        f"- 拒答路由：{'开启' if config.refusal_enabled else '关闭'}"
        f"，阈值 {config.refusal_score_threshold:.2f}（仅对重排分生效）",
        f"- 忠实度判定：{'开启，判定 ' + str(summary['judged_count']) + ' 道' if summary['judged_count'] else '未开启'}",
        "",
        "## 汇总",
        "",
        "| 指标 | 数值 |",
        "| --- | --- |",
        f"| 关键词覆盖率 | {summary['coverage']:.3f} |",
        f"| 全部关键词命中率 | {summary['all_keywords_rate']:.3f} |",
        f"| 来源命中率 | {summary['source_hit_rate']:.3f} |",
        f"| 回答引用来源率 | {summary['cites_source_rate']:.3f} |",
        f"| 有答案误拒答率 | {summary['answerable_refusal_rate']:.3f} |",
        f"| 无答案正确拒答率 | {summary['unanswerable_refusal_rate']:.3f} |",
        f"| 有答案路由拒答率 | {summary['answerable_route_refusal_rate']:.3f} |",
        f"| 无答案路由拒答率 | {summary['unanswerable_route_refusal_rate']:.3f} |",
    ]

    if summary["judged_count"]:
        lines.extend(
            [
                "",
                "## 忠实度判定（LLM 复查答案是否被原文支持）",
                "",
                f"- 判定样本：{summary['judged_count']} 道有答案题，拒答不参与",
                f"- 结论有原文支持的比例：{summary['faithful_rate']:.3f}",
                "",
                "| ID | 是否忠实 | 无依据的结论 | 判定理由 |",
                "| --- | --- | --- | --- |",
            ]
        )
        for record in records:
            if record.get("faithful") is None:
                continue
            claims = "；".join(record.get("unsupported_claims") or []) or "—"
            verdict = "是" if record["faithful"] else "否"
            lines.append(
                f"| {record['id']} | {verdict} | {claims} | "
                f"{record.get('judge_reason', '')} |"
            )

    lines.extend(
        [
            "",
            "## 拒答阈值扫描（仅按 Top-1 分数模拟）",
            "",
            "| 阈值 | 有答案误拒答率 | 无答案拒答率 |",
            "| ---: | ---: | ---: |",
        ]
    )
    for row in summary["thresholds"]:
        lines.append(
            f"| {row['threshold']:.1f} | "
            f"{row['answerable_false_refusal_rate']:.3f} | "
            f"{row['unanswerable_refusal_rate']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## 逐题结果",
            "",
            "| ID | 类型 | Top-1 分数 | 关键词覆盖 | 全部命中 | 引用来源 | 拒答 |",
            "| --- | --- | ---: | ---: | --- | --- | --- |",
        ]
    )
    for record in records:
        lines.append(
            f"| {record['id']} | "
            f"{'有答案' if record['answerable'] else '无答案'} | "
            f"{record['top_score'] if record['top_score'] is not None else '—'} | "
            f"{record['coverage'] if record['coverage'] is not None else '—'} | "
            f"{record['all_keywords']} | {record['cites_source']} | {record['refusal']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="运行答案级评测")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--answerable-limit", type=int, default=15)
    parser.add_argument("--unanswerable-limit", type=int, default=10)
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--results", default=str(DEFAULT_RESULTS))
    parser.add_argument(
        "--refusal-threshold",
        type=float,
        default=None,
        help="覆盖拒答阈值，用于和线上默认值做对比",
    )
    parser.add_argument(
        "--no-refusal",
        action="store_true",
        help="关闭拒答路由，只让模型自行判断是否有依据",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="用 LLM 复查答案结论是否被检索原文支持（忠实度）",
    )
    args = parser.parse_args()

    # 评测和线上共用同一份判断逻辑，这里只临时覆盖配置，不改代码路径。
    if args.no_refusal:
        config.refusal_enabled = False
    elif args.refusal_threshold is not None:
        config.refusal_score_threshold = args.refusal_threshold

    items = load_items(Path(args.dataset))
    answerable = select_evenly(
        [item for item in items if item["answerable"]],
        args.answerable_limit,
    )
    unanswerable = select_evenly(
        [item for item in items if not item["answerable"]],
        args.unanswerable_limit,
    )
    selected = answerable + unanswerable

    service = RagService()
    records: list[dict[str, Any]] = []
    for index, item in enumerate(selected, start=1):
        session_id = f"answer-eval-{item['id']}"
        documents, trace = service.retrieve_with_trace(
            item["question"],
            session_id=session_id,
        )
        # 依据不足时直接拒答，不调用生成模型；这条路径和线上完全一致。
        refused_route = should_refuse(trace)
        if refused_route:
            answer = REFUSAL_ANSWER
            service.record_turn(item["question"], answer, session_id)
        else:
            answer = service.invoke_answer(
                item["question"],
                session_id=session_id,
                documents=documents,
            )
        # 和应用走同一条补全逻辑，保证评测看到的引用和线上一致。
        answer = add_citations(answer, documents)
        metrics = evaluate_answer(item, answer, trace.top_sources)

        # 拒答题没有结论，不参与忠实度判定。
        judgement = None
        if args.judge and item["answerable"] and not refused_route:
            judgement = judge_faithfulness(item["question"], answer, documents)
        record = {
            "id": item["id"],
            "question": item["question"],
            "answerable": item["answerable"],
            "top_score": round(trace.top_score, 4) if trace.top_score is not None else None,
            "rerank_status": trace.rerank_status,
            "sources": trace.top_sources,
            "answer": answer,
            "answer_preview": _preview(answer),
            "refusal_route": refused_route,
            "faithful": None if judgement is None else judgement.supported,
            "unsupported_claims": (
                [] if judgement is None else judgement.unsupported_claims
            ),
            "judge_reason": "" if judgement is None else judgement.reason,
            **metrics,
        }
        records.append(record)
        print(
            f"[{index}/{len(selected)}] {item['id']} "
            f"answerable={item['answerable']} "
            f"score={record['top_score']} "
            f"route_refusal={refused_route} "
            f"coverage={record['coverage']} "
            f"faithful={record['faithful']} "
            f"refusal={record['refusal']}"
        )

    summary = summarize(records)
    Path(args.results).write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    Path(args.report).write_text(
        render_report(summary, records),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"report : {args.report}")
    print(f"results: {args.results}")


if __name__ == "__main__":
    main()
