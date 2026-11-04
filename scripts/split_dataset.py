"""按稳定哈希把 v2 评测集划分成 dev/test。

不依赖随机数，重复运行结果一致；test 约占 40%。
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def split_items(
    items: list[dict],
    test_buckets: int = 2,
    total_buckets: int = 5,
) -> tuple[list[dict], list[dict]]:
    dev: list[dict] = []
    test: list[dict] = []
    for item in items:
        digest = hashlib.md5(item["id"].encode("utf-8")).hexdigest()
        bucket = int(digest[:8], 16) % total_buckets
        (test if bucket < test_buckets else dev).append(item)

    # 保证两边都有有答案和无答案题，避免划分后无法计算关键指标。
    for flag in (True, False):
        if not any(item["answerable"] is flag for item in test):
            candidate = next(
                (item for item in reversed(dev) if item["answerable"] is flag),
                None,
            )
            if candidate is not None:
                dev.remove(candidate)
                test.append(candidate)
    return dev, test


def load_items(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_items(path: Path, items: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in items) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="划分 v2 评测集")
    parser.add_argument("--input", default="eval/dataset_v2.jsonl")
    parser.add_argument("--dev", default="eval/dataset_v2_dev.jsonl")
    parser.add_argument("--test", default="eval/dataset_v2_test.jsonl")
    args = parser.parse_args()

    items = load_items(Path(args.input))
    dev, test = split_items(items)
    write_items(Path(args.dev), dev)
    write_items(Path(args.test), test)
    print(f"total={len(items)} dev={len(dev)} test={len(test)}")
    print(f"dev_answerable={sum(1 for item in dev if item['answerable'])}")
    print(f"test_answerable={sum(1 for item in test if item['answerable'])}")


if __name__ == "__main__":
    main()
