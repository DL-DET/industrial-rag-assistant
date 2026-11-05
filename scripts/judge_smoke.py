"""判定器自检：用篡改过的答案确认 LLM 忠实度判定不是无脑放行。

评测里出现“全部忠实”时，必须先证明判定器真的会判错，
否则 1.000 可能只是判定器太宽松。

用法：
    python scripts/judge_smoke.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from eval.faithfulness import judge_faithfulness
from rag import RagService


DATASET = BASE_DIR / "eval" / "dataset_v2_test.jsonl"
ITEM_ID = "c04"

# 原文：胶带跑偏量不超过带宽的 5%，滚筒轴承温度不高于 70℃。
CASES = [
    ("忠实版", "空载调试时，胶带跑偏量不应超过带宽的5%，滚筒轴承温度应不高于70℃。"),
    ("方向说反", "空载调试时，胶带跑偏量不应超过带宽的5%，滚筒轴承温度应高于70℃。"),
    ("数字改错", "空载调试时，胶带跑偏量不应超过带宽的15%，滚筒轴承温度应不高于70℃。"),
    (
        "凭空补充",
        "空载调试时，胶带跑偏量不应超过带宽的5%，滚筒轴承温度应不高于70℃，"
        "且需要每季度更换一次润滑脂。",
    ),
]


def main() -> None:
    items = [
        json.loads(line)
        for line in DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    item = next(entry for entry in items if entry["id"] == ITEM_ID)
    print(f"问题：{item['question']}")

    documents, _ = RagService().retrieve_with_trace(item["question"])
    print(f"检索到 {len(documents)} 段原文\n")

    passed = 0
    for name, answer in CASES:
        result = judge_faithfulness(item["question"], answer, documents)
        expected = name == "忠实版"
        ok = result.supported is expected
        passed += 1 if ok else 0
        mark = "OK" if ok else "MISMATCH"
        print(f"[{mark}] {name}：supported={result.supported} — {result.reason}")
        if result.unsupported_claims:
            print(f"         无依据结论：{result.unsupported_claims}")

    print(f"\n{passed}/{len(CASES)} 个用例符合预期")


if __name__ == "__main__":
    main()
