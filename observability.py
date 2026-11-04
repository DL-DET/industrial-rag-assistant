"""查询 trace 与本地 JSONL 日志。"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import config_data as config


logger = logging.getLogger(__name__)
_LOG_LOCK = threading.Lock()


@dataclass
class QueryTrace:
    trace_id: str
    session_id: str = ""
    query_chars: int = 0
    candidate_count: int = 0
    returned_count: int = 0
    retrieval_ms: float = 0.0
    rerank_ms: float | None = None
    generation_ms: float | None = None
    rerank_status: str = "disabled"
    fallback: bool = False
    top_score: float | None = None
    top_sources: list[str] = field(default_factory=list)
    answer_chars: int = 0
    error: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )


def new_trace_id() -> str:
    return uuid4().hex[:12]


def write_trace(trace: QueryTrace, path: Path | None = None) -> None:
    """追加一条 trace；日志失败不能影响问答主链路。"""
    if not config.observability_enabled:
        return

    target = Path(path) if path is not None else Path(config.qa_log_path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(asdict(trace), ensure_ascii=False)
        with _LOG_LOCK:
            with target.open("a", encoding="utf-8") as file:
                file.write(line + "\n")
    except OSError:
        logger.warning("写入查询 trace 失败：%s", target, exc_info=True)
