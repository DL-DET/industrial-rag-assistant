"""DashScope 文本重排服务。

向量检索负责召回候选，重排模型负责把“真正回答问题的片段”排到前面。
重排是外部依赖：这里加了本地超时和连续失败熔断，避免拖垮问答主链路。
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from langchain_core.documents import Document

from dashscope import TextReRank

import config_data as config


logger = logging.getLogger(__name__)
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="rerank")


class RerankTimeout(RuntimeError):
    """重排调用超过本地等待时间。"""


class RerankService:
    def __init__(self, model: str | None = None):
        self.model = model or config.rerank_model
        self.timeout_seconds = config.rerank_timeout_seconds
        self.failure_threshold = config.rerank_failure_threshold
        self.cooldown_seconds = config.rerank_cooldown_seconds
        self._failure_count = 0
        self._open_until: float | None = None
        self._lock = threading.Lock()

    def available(self) -> bool:
        """熔断期间返回 False；冷却结束后进入半开，允许一次试探。"""
        with self._lock:
            if self._open_until is None:
                return True
            if time.monotonic() < self._open_until:
                return False
            self._failure_count = max(0, self.failure_threshold - 1)
            self._open_until = None
            return True

    def _record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._open_until = None

    def _record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._open_until = time.monotonic() + self.cooldown_seconds
                logger.warning(
                    "重排连续失败 %s 次，熔断 %.0f 秒",
                    self._failure_count,
                    self.cooldown_seconds,
                )

    def rerank(
        self,
        query: str,
        documents: list[Document],
        top_n: int | None = None,
    ) -> list[tuple[Document, float]]:
        """按问题相关性重排文档，返回 (文档, 重排分数) 列表。"""
        if not documents:
            return []
        if not self.available():
            raise RuntimeError("重排服务熔断中")

        try:
            future = _EXECUTOR.submit(
                TextReRank.call,
                model=self.model,
                query=query,
                documents=[document.page_content for document in documents],
                return_documents=False,
                top_n=top_n,
            )
            response = future.result(timeout=self.timeout_seconds)
        except FutureTimeoutError as exc:
            self._record_failure()
            raise RerankTimeout(
                f"重排超时（>{self.timeout_seconds:.1f}s）"
            ) from exc
        except Exception:
            self._record_failure()
            raise

        if getattr(response, "status_code", None) != 200:
            self._record_failure()
            raise RuntimeError(
                f"重排失败：{getattr(response, 'code', None)} "
                f"{getattr(response, 'message', None)}"
            )

        try:
            results = getattr(getattr(response, "output", None), "results", None) or []
            reranked: list[tuple[Document, float]] = []
            for item in results:
                index = int(item["index"])
                score = float(item["relevance_score"])
                if 0 <= index < len(documents):
                    reranked.append((documents[index], score))
        except Exception:
            self._record_failure()
            raise

        self._record_success()
        return reranked
