"""对比 LLM 忠实度判定与人工标注的一致率。

评测里出现"全部忠实"时，不能只报这个数字，还要知道判定器和人工判断差多远。

用法：
    python scripts/calibrate_judge.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


HUMAN_LABELS = BASE_DIR / "eval" / "human_labels.jsonl"
JUDGE_RESULTS = BASE_DIR / "eval" / "answer_results_test_judge.jsonl"


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def compare_labels(
    human: dict[str, bool],
    judge: dict[str, bool | None],
) -> dict:
    """按 id 对齐两份标注；judge 判定失败（None）的样本不计入分母。"""
    common = sorted(set(human) & set(judge))
    judged = [key for key in common if judge[key] is not None]
    agree = [key for key in judged if human[key] == judge[key]]
    disagreements = [
        {"id": key, "human": human[key], "judge": judge[key]}
        for key in judged
        if human[key] != judge[key]
    ]
    return {
        "compared": len(judged),
        "skipped": len(common) - len(judged),
        "agreement_rate": len(agree) / len(judged) if judged else None,
        "disagreements": disagreements,
    }


def confusion(human: dict[str, bool], judge: dict[str, bool | None]) -> dict[str, int]:
    """统计四种组合，看分歧偏向哪一边。"""
    judged = [key for key in human if judge.get(key) is not None]
    return {
        "both_faithful": sum(1 for key in judged if human[key] and judge[key]),
        "human_ok_judge_reject": sum(1 for key in judged if human[key] and not judge[key]),
        "human_reject_judge_ok": sum(1 for key in judged if not human[key] and judge[key]),
        "both_unfaithful": sum(1 for key in judged if not human[key] and not judge[key]),
    }


def main() -> None:
    human_rows = load_jsonl(HUMAN_LABELS)
    judge_rows = load_jsonl(JUDGE_RESULTS)

    human = {row["id"]: row["faithful"] for row in human_rows}
    reasons = {row["id"]: row.get("reason", "") for row in human_rows}
    judge = {
        row["id"]: row.get("faithful")
        for row in judge_rows
        if row.get("answerable") and row.get("faithful") is not None
    }

    result = compare_labels(human, judge)
    matrix = confusion(human, judge)

    print(f"人工标注：{len(human)} 条")
    print(f"参与对比：{result['compared']} 条")
    if result["skipped"]:
        print(f"judge 判定失败跳过：{result['skipped']} 条")
    if result["agreement_rate"] is None:
        print(
            "一致率：无可比样本"
            "（人工标注与 judge 结果没有交集，或 judge 全部判定失败）"
        )
        return
    print(f"一致率：{result['agreement_rate']:.3f}")

    print("\n混淆矩阵：")
    print(f"  双方都判忠实：      {matrix['both_faithful']}")
    print(f"  人工判忠实 / judge 判不忠实：{matrix['human_ok_judge_reject']}")
    print(f"  人工判不忠实 / judge 判忠实：{matrix['human_reject_judge_ok']}")
    print(f"  双方都判不忠实：    {matrix['both_unfaithful']}")

    if result["disagreements"]:
        print("\n分歧明细：")
        for item in result["disagreements"]:
            print(
                f"  {item['id']}  人工={item['human']}  judge={item['judge']}  "
                f"理由：{reasons.get(item['id'], '')}"
            )


if __name__ == "__main__":
    main()
