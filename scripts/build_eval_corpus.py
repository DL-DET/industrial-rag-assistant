"""把指定文件写入一个独立的评测向量库。

用途：做“换语料 / 去重”实验时，不覆盖应用正在使用的 chroma_db。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config_data as config
from file_parsers import extract_text_from_upload
from knowledge_base import KnowledgeBaseService


def build(
    files: list[Path],
    persist_dir: Path,
    collection: str,
    md5_path: Path,
) -> None:
    config.persist_directory = persist_dir.resolve()
    config.collection_name = collection
    config.md5_path = md5_path.resolve()
    config.persist_directory.mkdir(parents=True, exist_ok=True)
    config.md5_path.parent.mkdir(parents=True, exist_ok=True)

    service = KnowledgeBaseService()
    for path in files:
        text = extract_text_from_upload(path.name, path.read_bytes())
        result = service.upload_by_str(text, path.name)
        print(f"{path.name}: status={result.status} chunks={result.chunks}")


def main() -> None:
    parser = argparse.ArgumentParser(description="构建独立评测向量库")
    parser.add_argument("--persist-dir", required=True)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--md5-path", required=True)
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()

    build(
        files=[Path(name) for name in args.files],
        persist_dir=Path(args.persist_dir),
        collection=args.collection,
        md5_path=Path(args.md5_path),
    )


if __name__ == "__main__":
    main()
