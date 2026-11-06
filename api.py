"""FastAPI 服务：把现有 RAG 问答暴露为 HTTP 接口。

复用 RagService 的检索、重排、拒答、生成、引用补全和 trace，
不重复实现一套 RAG 逻辑。Streamlit 页面保持不变。

启动：
    uvicorn api:app --reload --port 8000

接口文档：
    http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import json
import logging
import re
import time
from functools import lru_cache
from typing import Any, Iterator
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.documents import Document
from pydantic import BaseModel, Field

import config_data as config
from citation import add_citations
from observability import QueryTrace, new_trace_id, write_trace
from rag import (
    PAGE_MARKER_PATTERN,
    REFUSAL_ANSWER,
    RagService,
    resolve_page_number,
    should_refuse,
)


logger = logging.getLogger(__name__)

SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


# ---------------------------------------------------------------------------
# 请求 / 响应模型
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="用户问题，最多 2000 字",
    )
    session_id: str | None = Field(
        default=None,
        max_length=80,
        description="会话 ID，只允许字母、数字、下划线和短横线；不传则自动生成",
    )


class SourceItem(BaseModel):
    source: str
    page: int | None = None
    excerpt: str = ""


class Timings(BaseModel):
    retrieval_ms: float = 0.0
    rerank_ms: float | None = None
    generation_ms: float | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    trace_id: str
    refused: bool = False
    fallback: bool = False
    rerank_status: str = "disabled"
    top_score: float | None = None
    timings: Timings


class HealthResponse(BaseModel):
    status: str
    api_key: bool
    vector_store: bool


# ---------------------------------------------------------------------------
# 服务依赖
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _build_rag_service() -> RagService:
    """只初始化一次，避免每个请求都重建 Chroma 和模型客户端。"""
    return RagService()


def get_rag_service() -> RagService:
    """FastAPI 依赖；初始化失败时返回 503，而不是 500。"""
    try:
        return _build_rag_service()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - 初始化失败需要统一转成 503
        logger.exception("RAG 服务初始化失败")
        raise HTTPException(
            status_code=503,
            detail="RAG 服务初始化失败，请检查知识库和模型配置",
        ) from exc


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def resolve_session_id(session_id: str | None) -> str:
    """校验并返回 session_id；不传时自动生成一个安全 ID。"""
    if not session_id:
        return uuid4().hex
    if not SESSION_ID_PATTERN.fullmatch(session_id):
        raise HTTPException(
            status_code=400,
            detail="session_id 只能包含字母、数字、下划线和短横线，长度 1-80",
        )
    return session_id


def normalize_question(question: str) -> str:
    """去掉首尾空白；纯空白按空问题处理。"""
    normalized = question.strip()
    if not normalized:
        raise HTTPException(status_code=422, detail="question 不能为空")
    return normalized


def document_sources(documents: list[Document]) -> list[dict[str, Any]]:
    """提取并去重引用信息，和 Streamlit 页面的引证卡保持同一口径。"""
    sources: list[dict[str, Any]] = []
    seen: dict[tuple[str, int | None], dict[str, Any]] = {}

    for document in documents:
        source = str(document.metadata.get("source", "未知来源"))
        page = resolve_page_number(document)
        excerpt = " ".join(
            PAGE_MARKER_PATTERN.sub("", document.page_content).split()
        )[:120]
        key = (source, page)
        if key in seen:
            if not seen[key]["excerpt"]:
                seen[key]["excerpt"] = excerpt
            continue
        entry = {"source": source, "page": page, "excerpt": excerpt}
        seen[key] = entry
        sources.append(entry)

    return sources


def trace_payload(trace: QueryTrace) -> dict[str, Any]:
    """把 trace 转成响应字段；耗时保留两位小数，None 保持 None。"""
    return {
        "trace_id": trace.trace_id,
        "refused": trace.refused,
        "fallback": trace.fallback,
        "rerank_status": trace.rerank_status,
        "top_score": trace.top_score,
        "timings": {
            "retrieval_ms": round(trace.retrieval_ms, 2),
            "rerank_ms": (
                round(trace.rerank_ms, 2) if trace.rerank_ms is not None else None
            ),
            "generation_ms": (
                round(trace.generation_ms, 2)
                if trace.generation_ms is not None
                else None
            ),
        },
    }


def sse_event(name: str, data: dict[str, Any]) -> str:
    """格式化为 SSE 帧；JSON 会转义换行，避免事件被截断。"""
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------------------
# 应用
# ---------------------------------------------------------------------------

app = FastAPI(
    title="工业设备 RAG API",
    version="1.0.0",
    description="复用现有 RagService 的检索、重排、拒答、生成与引用补全。",
)

# 演示版允许跨域；生产环境应改成具体域名。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "industrial-rag-api",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """不调用模型，只检查 API Key 和向量库是否就绪。"""
    readiness = config.runtime_readiness()
    ready = readiness["api_key"] and readiness["vector_store"]
    return HealthResponse(
        status="ok" if ready else "degraded",
        api_key=readiness["api_key"],
        vector_store=readiness["vector_store"],
    )


@app.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    service: RagService = Depends(get_rag_service),
) -> ChatResponse:
    """非流式问答：检索 → 拒答判断 → 生成 → 引用补全 → 写 trace。"""
    question = normalize_question(request.question)
    session_id = resolve_session_id(request.session_id)
    trace_id = new_trace_id()
    trace = QueryTrace(
        trace_id=trace_id,
        session_id=session_id,
        query_chars=len(question),
    )
    generation_started: float | None = None

    try:
        documents, trace = service.retrieve_with_trace(
            question,
            trace_id=trace_id,
            session_id=session_id,
        )
        sources = document_sources(documents)

        if should_refuse(trace):
            trace.refused = True
            trace.refusal_reason = "score_below_threshold"
            answer = REFUSAL_ANSWER
            trace.answer_chars = len(answer)
            service.record_turn(question, answer, session_id)
        else:
            generation_started = time.perf_counter()
            answer = service.invoke_answer(question, session_id, documents)
            trace.generation_ms = (time.perf_counter() - generation_started) * 1000
            answer = add_citations(answer, documents).strip() or "本次回答为空，请重试。"
            trace.answer_chars = len(answer)

        return ChatResponse(
            answer=answer,
            sources=[SourceItem(**item) for item in sources],
            **trace_payload(trace),
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - 统一返回带 trace_id 的错误
        trace.error = str(exc)
        logger.exception("问答失败 trace_id=%s", trace_id)
        raise HTTPException(
            status_code=500,
            detail=f"回答失败，trace_id={trace_id}",
        ) from exc
    finally:
        if generation_started is not None and trace.generation_ms is None:
            trace.generation_ms = (time.perf_counter() - generation_started) * 1000
        write_trace(trace)


@app.post("/chat/stream")
def chat_stream(
    request: ChatRequest,
    service: RagService = Depends(get_rag_service),
) -> StreamingResponse:
    """SSE 流式问答：meta → delta → done；拒答时只有 meta 和 done。"""
    question = normalize_question(request.question)
    session_id = resolve_session_id(request.session_id)
    trace_id = new_trace_id()
    trace = QueryTrace(
        trace_id=trace_id,
        session_id=session_id,
        query_chars=len(question),
    )

    def generate() -> Iterator[str]:
        nonlocal trace
        generation_started: float | None = None
        answer_chunks: list[str] = []

        try:
            documents, trace = service.retrieve_with_trace(
                question,
                trace_id=trace_id,
                session_id=session_id,
            )
            sources = document_sources(documents)
            refused = should_refuse(trace)
            trace.refused = refused
            if refused:
                trace.refusal_reason = "score_below_threshold"

            yield sse_event(
                "meta",
                {"sources": sources, **trace_payload(trace)},
            )

            if refused:
                answer = REFUSAL_ANSWER
                trace.answer_chars = len(answer)
                service.record_turn(question, answer, session_id)
                yield sse_event(
                    "done",
                    {"answer": answer, "sources": sources, **trace_payload(trace)},
                )
                return

            generation_started = time.perf_counter()
            for chunk in service.stream_answer(question, session_id, documents):
                answer_chunks.append(chunk)
                yield sse_event("delta", {"text": chunk})

            trace.generation_ms = (
                time.perf_counter() - generation_started
            ) * 1000
            answer = (
                add_citations("".join(answer_chunks).strip(), documents).strip()
                or "本次回答为空，请重试。"
            )
            trace.answer_chars = len(answer)
            yield sse_event(
                "done",
                {"answer": answer, "sources": sources, **trace_payload(trace)},
            )
        except Exception as exc:  # noqa: BLE001 - 流式错误也要给客户端一个事件
            trace.error = str(exc)
            logger.exception("流式问答失败 trace_id=%s", trace_id)
            yield sse_event(
                "error",
                {"message": f"回答失败，trace_id={trace_id}"},
            )
        finally:
            if generation_started is not None and trace.generation_ms is None:
                trace.generation_ms = (
                    time.perf_counter() - generation_started
                ) * 1000
            if answer_chunks and not trace.answer_chars:
                trace.answer_chars = len("".join(answer_chunks))
            write_trace(trace)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=False)
